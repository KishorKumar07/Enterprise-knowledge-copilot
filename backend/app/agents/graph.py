"""Wires the four agents into a single LangGraph graph:

    User -> Supervisor -> Retrieval -> Research -> Answer/Citation -> Response

The Supervisor's routing decision is used inside the Retrieval node (skip
search entirely for small talk) rather than as a separate conditional edge,
since every path still needs to reach the Answer node either way.
"""

from langgraph.graph import END, StateGraph

from app.agents.answer_agent import answer_node
from app.agents.research_agent import research_node
from app.agents.retrieval_agent import retrieval_node
from app.agents.state import AgentState
from app.agents.supervisor import supervisor_node


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("research", research_node)
    graph.add_node("answer_agent", answer_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "retrieval")
    graph.add_edge("retrieval", "research")
    graph.add_edge("research", "answer_agent")
    graph.add_edge("answer_agent", END)

    return graph.compile()
