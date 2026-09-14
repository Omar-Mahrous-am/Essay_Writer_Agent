import uuid
import logging
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage
from tavily import TavilyClient

from src.controllers.BaseController import BaseController
from src.helpers.config import settings
from src.schemas.queries import Queries
from src.stores.providers.templates.en_prompts import (
    PLAN_PROMPT,
    WRITER_PROMPT,
    RESEARCH_PLAN_PROMPT,
    REFLECTION_PROMPT,
    RESEARCH_CRITIQUE_PROMPT,
)

logger = logging.getLogger(__name__)

memory = MemorySaver()


class AgentState(TypedDict):
    task: str
    plan: str
    draft: str
    critique: str
    content: List[str]
    revision_number: int
    max_revisions: int


class EssayWriterAgentController(BaseController):
    """
    Controller orchestrating the multi-step LangGraph workflow for essay writing:
    1. Plan outline (planner)
    2. Research information for outline (research_plan)
    3. Generate essay draft (generate)
    4. Critique draft (reflect)
    5. Research supplementary info for critique (research_critique)
    6. Iterate until max_revisions reached
    """

    def __init__(self, model=None, search_client=None):
        super().__init__()

        # Initialize LLM model
        if model is not None:
            self.model = model
        else:
            model_name = settings.MODEL or "cohere:command-r-plus-08-2024"
            if "cohere" in model_name.lower():
                from langchain_cohere import ChatCohere
                cohere_model = model_name.split(":", 1)[-1] if ":" in model_name else model_name
                self.model = ChatCohere(
                    model=cohere_model,
                    cohere_api_key=settings.get_cohere_key()
                )
            else:
                from langchain_openai import ChatOpenAI
                self.model = ChatOpenAI(
                    model=model_name,
                    api_key=settings.OPENAI_API_KEY
                )

        self.client = self.model

        # Initialize Tavily search client
        if search_client is not None:
            self.tavily = search_client
        elif settings.TAVILY_API_KEY:
            self.tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
        else:
            self.tavily = None

        self.search_client = self.tavily

        # Setup StateGraph
        builder = StateGraph(AgentState)

        builder.add_node("planner", self.plan_node)
        builder.add_node("generate", self.generation_node)
        builder.add_node("reflect", self.reflection_node)
        builder.add_node("research_plan", self.research_plan_node)
        builder.add_node("research_critique", self.research_critique_node)

        builder.set_entry_point("planner")
        builder.add_conditional_edges(
            "generate",
            self.should_continue,
            {END: END, "reflect": "reflect"}
        )

        builder.add_edge("planner", "research_plan")
        builder.add_edge("research_plan", "generate")
        builder.add_edge("reflect", "research_critique")
        builder.add_edge("research_critique", "generate")

        self.workflow = builder.compile(checkpointer=memory)

    def plan_node(self, state: AgentState):
        messages = [
            SystemMessage(content=PLAN_PROMPT),
            HumanMessage(content=state["task"])
        ]
        response = self.model.invoke(messages)
        return {"plan": response.content}

    def research_plan_node(self, state: AgentState):
        queries = self.model.with_structured_output(Queries).invoke([
            SystemMessage(content=RESEARCH_PLAN_PROMPT),
            HumanMessage(content=state["task"])
        ])
        content = list(state.get("content") or [])
        if self.tavily and queries and hasattr(queries, "queries"):
            for q in queries.queries:
                try:
                    response = self.tavily.search(query=q, max_results=2)
                    for r in response.get("results", []):
                        if "content" in r:
                            content.append(r["content"])
                except Exception as e:
                    logger.warning("Tavily search failed for '%s': %s", q, e)
        return {"content": content}

    def generation_node(self, state: AgentState):
        content = "\n\n".join(state.get("content") or [])
        user_message = HumanMessage(
            content=f"{state['task']}\n\nHere is my plan:\n\n{state.get('plan', '')}"
        )
        messages = [
            SystemMessage(content=WRITER_PROMPT.format(content=content)),
            user_message
        ]
        response = self.model.invoke(messages)
        return {
            "draft": response.content,
            "revision_number": state.get("revision_number", 1) + 1
        }

    def reflection_node(self, state: AgentState):
        messages = [
            SystemMessage(content=REFLECTION_PROMPT),
            HumanMessage(content=state.get("draft", ""))
        ]
        response = self.model.invoke(messages)
        return {"critique": response.content}

    def research_critique_node(self, state: AgentState):
        queries = self.model.with_structured_output(Queries).invoke([
            SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
            HumanMessage(content=state.get("critique", ""))
        ])
        content = list(state.get("content") or [])
        if self.tavily and queries and hasattr(queries, "queries"):
            for q in queries.queries:
                try:
                    response = self.tavily.search(query=q, max_results=2)
                    for r in response.get("results", []):
                        if "content" in r:
                            content.append(r["content"])
                except Exception as e:
                    logger.warning("Tavily critique search failed for '%s': %s", q, e)
        return {"content": content}

    def should_continue(self, state: AgentState):
        if state.get("revision_number", 1) > state.get("max_revisions", 2):
            return END
        return "reflect"

    def run(self, task: str, max_revisions: int = 2) -> dict:
        """Executes the workflow graph with checkpointer and returns the final state."""
        initial_state: AgentState = {
            "task": task,
            "plan": "",
            "draft": "",
            "critique": "",
            "content": [],
            "revision_number": 1,
            "max_revisions": max_revisions,
        }
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        return self.workflow.invoke(initial_state, config=config)
