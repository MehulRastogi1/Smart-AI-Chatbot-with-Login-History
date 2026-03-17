import streamlit as st

def sidebar():
    st.sidebar.title("⚡ AI Assistant")
    if not st.session_state.logged_in:
        page = st.sidebar.radio(
            "Navigation",
            ["Home", "Chatbot","Login"]
        )
        
    else:
        page = st.sidebar.radio(
            "Navigation",
            ["Home", "Chatbot","Logout"]
        )
        
    st.sidebar.markdown("---")
    
    
    return page