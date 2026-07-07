# core/orchestrator.py
from typing import TypedDict
from langgraph.graph import StateGraph, END

from core.ollama_client import OllamaClient
from core.attacker import Attacker
from core.judge import Judge
from data.attack_taxonomy import ATTACK_CATEGORIES,PROBE_TOPICS

import json
import time
from pathlib import Path

class RTState(TypedDict):
    category: str
    topic: str
    round_num: int
    max_rounds: int
    current_prompt: str
    target_response: str
    verdict: str
    history: list


def node_generate(state: RTState) -> RTState:
    if state["round_num"] == 0:
        prompt = attacker.generate_attack(state["category"], state["topic"])
    else:
        last = state["history"][-1]
        prompt = attacker.mutate_attack(last["prompt"], last["response"], state["category"])
    state["current_prompt"] = prompt
    return state


def node_query_target(state: RTState) -> RTState:
    response = target.chat([{"role": "user", "content": state["current_prompt"]}])
    state["target_response"] = response
    return state


def node_judge(state: RTState) -> RTState:
    result = judge.score(state["current_prompt"], state["target_response"])
    state["verdict"] = result["verdict"]
    state["history"].append({
        "round": state["round_num"],
        "prompt": state["current_prompt"],
        "response": state["target_response"],
        "verdict": result["verdict"],
        "reasoning": result.get("reasoning", ""),
    })
    state["round_num"] += 1
    return state


def route_after_judge(state: RTState) -> str:
    if state["verdict"] == "FAIL":
        return "stop"          
    if state["round_num"] >= state["max_rounds"]:
        return "stop"          
    return "retry"             


graph = StateGraph(RTState)

graph.add_node("generate", node_generate)
graph.add_node("query_target", node_query_target)
graph.add_node("judge", node_judge)

graph.set_entry_point("generate")           
graph.add_edge("generate", "query_target")  
graph.add_edge("query_target", "judge")     


graph.add_conditional_edges(
    "judge",
    route_after_judge,
    {
        "retry": "generate",  
        "stop": END,          
    },
)

app = graph.compile()  

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

def run_campaign(max_rounds=3):
    all_results=[]

    for category in ATTACK_CATEGORIES:
        for topic in PROBE_TOPICS:
            print(f"Running category={category!r} topic={topic!r}")
            initial_state: RTState = {
                                        "category": category,
                                        "topic": topic,
                                        "round_num": 0,
                                        "max_rounds": max_rounds,
                                        "current_prompt": "",
                                        "target_response": "",
                                        "verdict": "",
                                        "history": [],
                                    }
            final_state = app.invoke(initial_state)
            all_results.append({
                "category": category,
                "topic": topic,
                "final_verdict":final_state['history'][-1]['verdict'],
                "rounds_taken":final_state['round_num'],
                "history":final_state["history"]
            })
    run_id = f"run_{int(time.time())}"
    out_path = RESULTS_DIR / f"{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nSaved {len(all_results)} results to {out_path}")
    return all_results

if __name__ == "__main__":
    attacker = Attacker(OllamaClient(model="gemma3:4b", temperature=0.9))
    target = OllamaClient(model="gemma3:4b", temperature=0.7)
    judge = Judge(OllamaClient(model="gemma3:4b"))
    run_campaign(max_rounds=3)