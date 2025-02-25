#core/agents.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.agents import AgentActionMessageLog, AgentFinish
from langchain_core.messages import AIMessage
from .tools import SUPPORT_TOOLS, ToolExecutor, escalate_to_human
from server.database import get_vector_store
from core.evaluator import evaluate_response
from dotenv import load_dotenv
import os
import logging
import asyncio
import json
from datetime import datetime, timedelta
import pytz

load_dotenv()
logger = logging.getLogger(__name__)

# Define our expected state structure.
class AgentState(TypedDict):
    intermediate_steps: List[dict]
    context: List[str]
    query: str
    user_id: str
    response: str
    needs_escalation: bool
    tool_outputs: List[str]
    escalation_reason: Optional[str]
    tool_calls: Optional[List[dict]]

# Helper function to merge updates into an existing state.
def merge_state(old: AgentState, updates: dict) -> AgentState:
    new_state = old.copy()
    new_state.update(updates)
    defaults = {
       "intermediate_steps": [],
       "context": [],
       "query": "",
       "user_id": "",
       "response": "",
       "needs_escalation": False,
       "tool_outputs": [],
       "escalation_reason": None,
       "tool_calls": None
    }
    for key, value in defaults.items():
        if key not in new_state or new_state[key] is None:
            new_state[key] = value
    return new_state

class SupportAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self.tool_executor = ToolExecutor(SUPPORT_TOOLS)
        self.workflow = StateGraph(AgentState)
        self._build_workflow()

    def _build_workflow(self):
        self.workflow.add_node("init", self.initialize_state)
        self.workflow.add_node("retrieve_context", self.retrieve_context)
        self.workflow.add_node("analyze_intent", self.analyze_intent)
        self.workflow.add_node("execute_tools", self.execute_tools)
        self.workflow.add_node("generate_response", self.generate_response)
        self.workflow.add_node("evaluate_escalation", self.evaluate_escalation)
        self.workflow.add_node("escalate", self.escalate)

        # Set up the workflow edges
        self.workflow.set_entry_point("init")
        self.workflow.add_edge("init", "retrieve_context")
        self.workflow.add_edge("retrieve_context", "analyze_intent")
        
        # Add conditional edges from analyze_intent
        self.workflow.add_conditional_edges(
            "analyze_intent",
            self.decide_next_step,
            {
                "tool_use": "execute_tools",
                "escalate": "escalate",
                "direct_response": "generate_response"
            }
        )
        
        # Complete the workflow
        self.workflow.add_edge("execute_tools", "generate_response")
        self.workflow.add_edge("generate_response", "evaluate_escalation")
        self.workflow.add_conditional_edges(
            "evaluate_escalation",
            self.decide_escalation,
            {"escalate": "escalate", "final": END}
        )
        self.workflow.add_edge("escalate", END)

    def initialize_state(self, state: AgentState) -> AgentState:
        updates = {
            "intermediate_steps": [],
            "context": [],
            "query": state.get("query", ""),
            "user_id": state.get("user_id", ""),
            "response": "",
            "needs_escalation": False,
            "tool_outputs": [],
            "escalation_reason": None,
            "tool_calls": None
        }
        new_state = merge_state(state, updates)
        logger.info(f"Initialized state: {new_state}")
        return new_state

    async def retrieve_context(self, state: AgentState) -> AgentState:
        try:
            store = get_vector_store()
            # Run the blocking similarity search in a separate thread.
            docs = await asyncio.to_thread(lambda query: store.similarity_search(query, k=3), state["query"])
            context = [f"{d.metadata.get('source', '')}: {d.page_content}" for d in docs]
            logger.info(f"Retrieved {len(context)} context items.")
            return merge_state(state, {"context": context})
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            return merge_state(state, {"context": []})

    def analyze_intent(self, state: AgentState) -> AgentState:
        try:
            new_state = merge_state(state, {})
            current_time = datetime.now(pytz.UTC)
            tomorrow = current_time + timedelta(days=1)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an AI support agent. Analyze the query and return a JSON response.
For each query, respond with ONLY a JSON object following these formats:

For weather queries:
{{"action": "tool", "tool_name": "get_weather", "tool_args": {{"city": "<CITY_NAME>"}}}}

For calendar queries:
{{"action": "tool", "tool_name": "schedule_event", "tool_args": {{"title": "<TITLE>", "start_time": "<ISO_TIME>", "duration": <MINUTES>}}}}

For web searches:
{{"action": "tool", "tool_name": "web_search", "tool_args": {{"query": "<SEARCH_QUERY>", "max_results": 3}}}}

For order tracking:
{{"action": "tool", "tool_name": "check_order_status", "tool_args": {{"order_id": "<ORDER_ID>"}}}}

For product questions:
{{"action": "rag", "context_needed": true}}

For escalation:
{{"action": "escalate", "reason": "<REASON>"}}

For general conversation:
{{"action": "direct", "response": "<YOUR_RESPONSE>"}}

Current time (PKT): {current_time}
Tomorrow (PKT): {tomorrow}

RESPOND WITH VALID JSON ONLY. NO OTHER TEXT."""),
                ("user", "Query: {query}")
            ]).partial(
                current_time=current_time.isoformat(),
                tomorrow=tomorrow.isoformat()
            )

            logger.info(f"Processing query: {new_state['query']}")
            response = self.llm.invoke(
                prompt.invoke({
                    "query": new_state["query"]
                })
            )

            try:
                # Clean the response content to ensure it's valid JSON
                content = response.content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                logger.info(f"Raw LLM response: {content}")
                parsed = json.loads(content)
                logger.info(f"Parsed intent: {parsed}")

                if parsed["action"] == "tool":
                    if parsed["tool_name"] == "schedule_event":
                        start_time = parsed["tool_args"].get("start_time", "")
                        if not start_time.endswith('Z'):
                            local_tz = pytz.timezone('Asia/Karachi')
                            local_dt = datetime.fromisoformat(start_time)
                            if local_dt.tzinfo is None:
                                local_dt = local_tz.localize(local_dt)
                            utc_dt = local_dt.astimezone(pytz.UTC)
                            parsed["tool_args"]["start_time"] = utc_dt.isoformat()

                    new_state["tool_calls"] = [{
                        "name": parsed["tool_name"],
                        "args": parsed["tool_args"]
                    }]
                    logger.info(f"Tool call configured: {parsed['tool_name']}")
                    
                elif parsed["action"] == "escalate":
                    new_state["needs_escalation"] = True
                    new_state["escalation_reason"] = parsed.get("reason")
                    logger.info(f"Escalation needed: {parsed.get('reason')}")
                    
                elif parsed["action"] == "rag":
                    new_state["response"] = "Let me search our documentation..."
                    
                else:
                    new_state["response"] = parsed.get("response", "")

                return new_state

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                logger.error(f"Failed to parse: {content}")
                new_state["needs_escalation"] = True
                new_state["escalation_reason"] = "Failed to parse response"
                return new_state

        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            return state

    def decide_next_step(self, state: AgentState) -> str:
        """Determine the next step based on the current state."""
        if state.get("needs_escalation"):
            logger.info("Deciding next step: escalate")
            return "escalate"
        elif state.get("tool_calls"):
            logger.info("Deciding next step: tool_use")
            return "tool_use"
        logger.info("Deciding next step: direct_response")
        return "direct_response"

    async def execute_tools(self, state: AgentState) -> AgentState:
        """Execute tool calls and update state with results."""
        new_state = state.copy()
        outputs = []
        
        try:
            for tool_call in new_state.get("tool_calls", []):
                logger.info(f"Executing tool: {tool_call['name']}")
                output = await self.tool_executor.execute(
                    tool_call["name"],
                    tool_call["args"]
                )
                outputs.append(f"{tool_call['name']}: {output}")
                logger.info(f"Tool execution successful: {output}")
            
            new_state["tool_outputs"] = outputs
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            new_state["tool_outputs"] = [f"Error processing request: {str(e)}"]
        
        return new_state

    def generate_response(self, state: AgentState) -> AgentState:
        new_state = state.copy()
        try:
            # Prepare prompt with context and tool outputs
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI assistant. Use any provided context and tool outputs to generate an accurate, concise, and friendly response. When needed, apply retrieval-augmented generation (RAG) and call the appropriate tools. If no additional context is given, simply engage in general conversation naturally. Keep your reply brief, clear, and include appropriate emojis.
."""),
                ("user", """Query: {query}
                Context: {context}
                Tool Outputs: {tool_outputs}""")
            ])

            response = prompt.invoke({
                "query": new_state["query"],
                "context": "\n".join(new_state["context"]) if new_state["context"] else "No context available",
                "tool_outputs": "\n".join(new_state["tool_outputs"]) if new_state["tool_outputs"] else "No tool outputs"
            })

            new_state["response"] = self.llm.invoke(response).content
            logger.info("Generated response successfully")
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            new_state["response"] = "I apologize, but I'm having trouble generating a response. 😅"
        return new_state

    def evaluate_escalation(self, state: AgentState) -> AgentState:
        # Use dynamic evaluation based on the query and generated response.
        eval_result = evaluate_response(state["query"], state["response"])
        update = {
            "needs_escalation": eval_result.needs_escalation,
            "escalation_reason": "High urgency" if eval_result.needs_escalation else None
        }
        new_state = merge_state(state, update)
        logger.info(f"Evaluation complete. Needs escalation: {new_state['needs_escalation']}")
        return new_state

    def decide_escalation(self, state: AgentState) -> str:
        return "escalate" if state["needs_escalation"] else "final"

    async def escalate(self, state: AgentState) -> AgentState:
        """Handle escalation to human support."""
        new_state = state.copy()
        try:
            # Create escalation request
            escalation_data = {
                "query": new_state["query"],
                "user_id": new_state["user_id"],
                "reason": new_state.get("escalation_reason", "Escalation requested")
            }
            
            logger.info(f"Attempting escalation with data: {escalation_data}")
            
            # Call escalation tool
            result = await SUPPORT_TOOLS[3].ainvoke(input=escalation_data)
            
            if result:
                new_state["response"] = result
                logger.info("Escalation successful")
            else:
                raise Exception("Escalation failed")
                
        except Exception as e:
            logger.error(f"Escalation failed: {str(e)}")
            new_state["response"] = "⚠️ I couldn't escalate your query. Please try again later."
        
        return new_state



agent = SupportAgent()
workflow = agent.workflow
