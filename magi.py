# MAGI - Research Agent (ver. 1.5) 

from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langgraph.graph import START, END, StateGraph
from langgraph.types import Send
from tavily import TavilyClient

from schemas import *
from prompts import *

from prompts import review_prompt

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

# Initialize Language Models (LLMs)
# 'llama3.1:8b-instruct-q4_K_S' is used for general LLM tasks and structured output.
llm = ChatOllama(model = 'llama3.1:8b-instruct-q4_K_S')
# 'deepseek-r1:8b' is used specifically for reasoning tasks, such as final writing and review.
reasoning_llm = ChatOllama(model = 'deepseek-r1:8b')


# Helper function to update progress in Streamlit
def update_progress(percentage: int, message: str):
    """Updates the progress bar and status message in Streamlit."""
    if 'progress_bar' in st.session_state and 'status_text' in st.session_state:
        current_progress = st.session_state.get('current_progress', 0)
        # Only increase progress if the new percentage is greater
        if percentage > current_progress:
            st.session_state['progress_bar'].progress(percentage)
            st.session_state['current_progress'] = percentage
        st.session_state['status_text'].text(message)

# Helper function to extract the thinking string (kept for robustness, though not displayed)
def extract_thinking_string(llm_content: str) -> tuple[str, str]:
    """
    Extracts the 'thinking string' from LLM content that contains the </think> tag.
    Returns the thinking string and the remaining content.
    """
    if "</think>" in llm_content:
        parts = llm_content.split("</think>", 1)
        thinking = parts[0].strip()
        remaining_content = parts[1].strip()
        return thinking, remaining_content
    return "", llm_content # Returns empty if no tag


# Nodes (Graph Nodes)

# Node to build the first search queries.
def build_first_queries(state: ReportState):
    update_progress(10, "Generating search queries...")
    class QueryList(BaseModel):
        queries: List[str]

    user_input = state.user_input
    prompt = build_queries.format(user_input = user_input)
    query_llm = llm.with_structured_output(QueryList)
    result = query_llm.invoke(prompt)

    # We store the queries and a placeholder for thinking, as per the new requirement
    return {
        'queries': result.queries,
        'build_queries_thinking': "Query generation process completed." # Placeholder for internal use, not displayed
    }


# Node to "spawn" individual researchers (one for each query).
def spawn_researchers(state: ReportState):
    update_progress(20, "Initiating parallel searches...")
    return [Send("single_search", (query, state.user_input))
            for query in state.queries]

# Node to perform a single web search and summarize the results.
def single_search(input_tuple: tuple):
    query, user_input = input_tuple

    current_progress = st.session_state.get('current_progress', 20)
    update_progress(current_progress, f"Searching and summarizing: '{query[:40]}...'")

    tavily_client = TavilyClient()
    results = tavily_client.search(query,
                         max_results=5,
                         include_raw_content=False)

    query_results = []
    for result in results["results"]:
        url = result["url"]
        url_extraction = tavily_client.extract(url)

        if len(url_extraction["results"]) > 0:
            raw_content = url_extraction["results"][0]["raw_content"]
            prompt = resume_search.format(user_input=user_input,
                                        search_results=raw_content)

            llm_result = llm.invoke(prompt)
            query_results += [QueryResults(title=result["title"],
                                    url=url,
                                    resume=llm_result.content)]
    return {"queries_results": query_results}

# Node to compile the final response based on all summarized results.
def final_writer(state: ReportState):
    update_progress(70, "Compiling final response...")

    search_results = ""
    references = ""
    for i, result in enumerate(state.queries_results):
        search_results += f"[{i+1}]\n\n"
        search_results += f"Title: {result.title}\n"
        search_results += f"URL: {result.url}\n"
        search_results += f"Content: {result.resume}\n"
        search_results += f"================\n\n"

        references += f"[{i+1}] - [{result.title}]({result.url})\n"

    prompt = build_final_response.format(user_input=state.user_input,
                                    search_results=search_results)

    llm_result = reasoning_llm.invoke(prompt)

    # Extract thinking string and actual content from the final response
    final_writer_thinking, final_response_content = extract_thinking_string(llm_result.content)

    final_response = final_response_content + "\n\n References:\n" + references

    return {
        "final_response": final_response,
        "final_writer_thinking": final_writer_thinking # Store writer's thinking for internal record
    }

# Node to review the generated final response.
def reviewer(state: ReportState):
    update_progress(90, "Reviewing and validating the response...")
    final_response_to_review = state.final_response
    user_question = state.user_input

    summaries_for_reviewer = ""
    for i, result in enumerate(state.queries_results):
        summaries_for_reviewer += f"Source [{i+1}] - Title: {result.title}\n"
        summaries_for_reviewer += f"Content Summary:\n{result.resume}\n"
        summaries_for_reviewer += f"-----------------\n"

    prompt = review_prompt.format(
        user_input=user_question,
        final_response=final_response_to_review,
        search_results_summaries=summaries_for_reviewer
    )

    review_result = reasoning_llm.invoke(prompt)
    reviewer_raw_content = review_result.content.strip()

    reviewer_thinking = "Reviewer assessed the response." # Default placeholder for internal record

    final_response_edited_content = final_response_to_review
    feedback_to_return = ""

    if "The Final Response is coherent, accurate, and fully supported by the provided sources." in reviewer_raw_content:
        feedback_to_return = "The Final Response is coherent, accurate, and fully supported by the provided sources."
        final_response_edited_content = final_response_to_review
        reviewer_thinking = feedback_to_return
    elif "<CORRECTED_FINAL_RESPONSE>" in reviewer_raw_content and "</CORRECTED_FINAL_RESPONSE>" in reviewer_raw_content:
        feedback_parts = reviewer_raw_content.split("<CORRECTED_FINAL_RESPONSE>")
        feedback_to_return = feedback_parts[0].strip()
        corrected_response_block = feedback_parts[1].split("</CORRECTED_FINAL_RESPONSE>")[0].strip()
        final_response_edited_content = corrected_response_block
        reviewer_thinking = feedback_to_return
    else:
        feedback_to_return = "Reviewer generated unexpected format or direct feedback:\n" + reviewer_raw_content
        final_response_edited_content = final_response_to_review
        reviewer_thinking = "Unexpected review format. Raw content:\n" + reviewer_raw_content

    print(f"\n--- Final Feedback from Reviewer (for exhibition) ---\n{feedback_to_return}\n---------------------------\n")
    print(f"\n--- Final Response Edited (for exhibition) ---\n{final_response_edited_content}\n---------------------------\n")

    return {
        "review_feedback": feedback_to_return,
        "final_response_edited": final_response_edited_content,
        "reviewer_thinking": reviewer_thinking # Store reviewer's thinking/feedback for internal record
    }


# Edges (Graph Edges - define execution flow)
builder = StateGraph(ReportState) # Initialize state graph with ReportState.

# Add all nodes to the graph.
builder.add_node('build_first_queries', build_first_queries)
builder.add_node('single_search', single_search)
builder.add_node('final_writer', final_writer)
builder.add_node('reviewer', reviewer) # Added reviewer node

# Define edges (transitions) between nodes.
builder.add_edge(START, 'build_first_queries') # Flow starts with query building.
builder.add_conditional_edges('build_first_queries',
                              spawn_researchers,
                              ['single_search'])
builder.add_edge('single_search', 'final_writer')
builder.add_edge('final_writer', 'reviewer')
builder.add_edge('reviewer', END)
graph = builder.compile()

# Main block for Streamlit execution.
if __name__ == '__main__':
    st.title('🔎 MAGI - Research Agent (ver. 1.5)')
    user_input = st.text_input('Ask something (e.g., "What are the latest advancements in AI for drug discovery?")')

    if st.button("Research"):
        # Initialize progress bar and text placeholder
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Store progress object in session_state for access by nodes
        st.session_state['progress_bar'] = progress_bar
        st.session_state['status_text'] = status_text
        st.session_state['current_progress'] = 0

        with st.spinner("Starting MAGI process..."):
            final_state = graph.invoke({"user_input": user_input})

            # Retrieve only the necessary outputs for display
            chosen_queries = final_state.get("queries", [])
            final_response_edited = final_state.get("final_response_edited", "No final response generated.")

        # Ensure progress bar reaches 100% at the end
        if 'progress_bar' in st.session_state:
            st.session_state['progress_bar'].progress(100)
        if 'status_text' in st.session_state:
            st.session_state['status_text'].text("Research and review completed!")

        # Clear session_state objects after use
        if 'progress_bar' in st.session_state:
            del st.session_state['progress_bar']
        if 'status_text' in st.session_state:
            del st.session_state['status_text']
        if 'current_progress' in st.session_state:
            del st.session_state['current_progress']

        # Display chosen queries
        with st.expander("✅ Generated Queries", expanded=False):
            if chosen_queries:
                for i, query in enumerate(chosen_queries):
                    st.markdown(f"- {query}")
            else:
                st.write("No queries were generated.")

        # Display the final edited response
        st.subheader("Final Research Report")
        st.write(final_response_edited) # No specific title, just the content