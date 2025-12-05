"""
Streamlit UI for Text-to-SQL System

A modern, interactive interface for the Agentic Text-to-SQL system.

Features:
- Clean, professional design
- Real-time query execution
- SQL query display with syntax highlighting
- Chain-of-Thought reasoning display
- Side-by-side table and chart display
- Error handling with helpful messages

Production-grade features:
- Responsive layout
- Loading states
- Error boundaries
- Session state management
- Professional styling
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

from agents.graph import run_agent
from core.config import get_config


# Page configuration
st.set_page_config(
    page_title="Text-to-SQL Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for modern styling
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 2rem;
    }
    
    /* Headers */
    h1 {
        color: #1f77b4;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #2c3e50;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    h3 {
        color: #34495e;
        font-weight: 500;
    }
    
    /* Code blocks */
    .stCodeBlock {
        background-color: #f8f9fa;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* Success messages */
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    /* Error messages */
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #1f77b4;
        color: white;
        font-weight: 600;
        padding: 0.5rem 2rem;
        border-radius: 0.5rem;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #155a8a;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Text input */
    .stTextInput > div > div > input {
        border-radius: 0.5rem;
        border: 2px solid #e0e0e0;
        padding: 0.75rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1f77b4;
        box-shadow: 0 0 0 0.2rem rgba(31, 119, 180, 0.25);
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the application header."""
    st.title("Text-to-SQL Agent")
    st.markdown("""
    **Powered by LangGraph & Google Gemini**
    
    Ask questions about the Chinook music store database in natural language, 
    and get SQL queries with visualizations!
    """)
    st.divider()


def render_sidebar():
    """Render the sidebar with information and examples."""
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This is an **Agentic Text-to-SQL System** that:
        
        - Uses LangGraph for workflow orchestration
        - Employs Chain-of-Thought reasoning
        - Validates SQL for safety and correctness
        - Self-corrects errors automatically
        - Recommends appropriate visualizations
        - Shows data table alongside charts
        """)
        
        st.divider()
        
        st.header("Example Questions")
        
        examples = [
            "Show me the top 5 best-selling tracks",
            "Which customers are from Brazil?",
            "What's the total revenue by country?",
            "Which genre has the most tracks?",
            "Who are the top 3 customers by total spending?",
            "Which employees have the most customers?",
            "Show me all albums by Led Zeppelin",
            "What's the average track length by genre?",
        ]
        
        for example in examples:
            if st.button(example, key=f"example_{example}", use_container_width=True):
                st.session_state.question = example
                st.rerun()
        
        st.divider()
        
        st.header("Configuration")
        config = get_config()
        st.markdown(f"""
        - **SQL Generator**: `{config.sql_generator_model}`
        - **Router**: `{config.router_model}`
        - **Max Retries**: {config.max_retry_count}
        - **Result Limit**: {config.max_result_rows} rows
        """)


def render_visualization(
    results: List[Dict[str, Any]],
    viz_spec: Dict[str, Any]
):
    """
    Render data visualization based on specification.
    Shows table and chart side-by-side when chart is recommended.
    
    Args:
        results: Query results
        viz_spec: Visualization specification from agent
    """
    if not results:
        st.info("No results to visualize.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    chart_type = viz_spec.get("chart_type", "table")
    
    # If chart type is table only, show full-width table
    if chart_type == "table":
        st.dataframe(df, use_container_width=True, hide_index=True)
        return
    
    # For charts, show table and chart side-by-side
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Data Table**")
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    
    with col2:
        st.markdown("**Visualization**")
        
        x_col = viz_spec.get("x_column")
        y_col = viz_spec.get("y_column")
        title = viz_spec.get("title", f"{chart_type.title()} Chart")
        
        # Validate columns exist
        if not (x_col and y_col and x_col in df.columns and y_col in df.columns):
            st.warning("Could not create chart. Column specification invalid.")
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
            return
        
        # Create appropriate chart
        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title)
            fig.update_layout(
                template="plotly_white",
                title_font_size=18,
                title_font_color="#1f77b4",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
            fig.update_layout(
                template="plotly_white",
                title_font_size=18,
                title_font_color="#1f77b4",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title)
            fig.update_layout(
                template="plotly_white",
                title_font_size=18,
                title_font_color="#1f77b4",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.warning(f"Unknown chart type: {chart_type}")
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)


def main():
    """Main application logic."""
    # Initialize session state
    if "question" not in st.session_state:
        st.session_state.question = ""
    if "results" not in st.session_state:
        st.session_state.results = None
    
    # Render UI components
    render_header()
    render_sidebar()
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        question = st.text_input(
            "Ask a question about the music store:",
            value=st.session_state.question,
            placeholder="e.g., Show me the top 10 selling artists",
            key="question_input"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        submit = st.button("Generate SQL", use_container_width=True)
    
    # Process query
    if submit and question:
        with st.spinner("Analyzing your question..."):
            try:
                # Run agent
                result_state = run_agent(question)
                st.session_state.results = result_state
                
            except Exception as e:
                st.error(f"ERROR: An error occurred: {str(e)}")
                st.session_state.results = None
    
    # Display results
    if st.session_state.results:
        state = st.session_state.results
        
        # Check if question was relevant
        if not state.is_relevant:
            st.warning("WARNING: " + state.final_response)
            return
        
        # Check for errors
        if state.final_response and ("Error" in state.final_response or "apologize" in state.final_response):
            st.error("ERROR: " + state.final_response)
            
            # Show failed SQL if available
            if state.sql_query:
                st.subheader("Failed SQL Query")
                st.code(state.sql_query, language="sql")
            
            return
        
        # Success! Display results
        st.success("SUCCESS: " + state.final_response)
        
        # Display reasoning
        if state.reasoning:
            with st.expander("Chain-of-Thought Reasoning", expanded=False):
                st.markdown(state.reasoning)
        
        # Display SQL query
        st.subheader("Generated SQL Query")
        st.code(state.sql_query, language="sql")
        
        # Display results
        if state.query_result:
            st.subheader("Results")
            
            # Render visualization (table + chart side-by-side)
            viz_spec = state.visualization_spec or {"chart_type": "table"}
            render_visualization(state.query_result, viz_spec)
            
            # Show row count
            row_count = len(state.query_result)
            st.caption(f"Showing {row_count} row(s)")
        else:
            st.info("Query executed successfully but returned no results.")


if __name__ == "__main__":
    main()
