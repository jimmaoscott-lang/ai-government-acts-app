import streamlit as st
import os
from openai import OpenAI
import json

# Note: This app uses the xAI Grok API. To set it up:
# 1. Sign up for xAI API access at https://x.ai/api
# 2. Create a Streamlit app in Streamlit Cloud (free tier), link your GitHub repo.
# 3. In Streamlit Cloud secrets, add: XAI_API_KEY = "your_api_key_here"
# 4. The app runs without students needing to input any API keys.
# Assumptions: xAI API is OpenAI-compatible for chat completions (as per current docs).
# If not, adjust the client accordingly.
# For comic strips, this generates text-based panels with descriptions (visuals can be added later via image gen API if available).

# Initialize the client
@st.cache_resource
def init_client():
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        st.error("XAI_API_KEY not set in Streamlit secrets. Please configure it.")
        st.stop()
    return OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",  # xAI base URL
    )

client = init_client()

# App title
st.title("AI Helper for U.S. Government Acts")
st.write("Welcome! This app helps you create something fun about one of these important U.S. laws (called 'acts'). Pick one, choose what to make, and I'll ask simple questions to build it with your ideas. We'll go step by step!")

# Sidebar for selections (persistent across reruns)
if "act" not in st.session_state:
    st.session_state.act = None
if "project_type" not in st.session_state:
    st.session_state.project_type = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = None
if "gathering_info" not in st.session_state:
    st.session_state.gathering_info = True
if "final_project" not in st.session_state:
    st.session_state.final_project = None

# Acts list
acts = [
    "22nd Amendment (1951) - Limits presidents to two terms.",
    "25th Amendment (1967) - Handles what happens if the president can't do their job.",
    "Pendleton Act (1883) - Makes government jobs based on skills, not politics.",
    "Hatch Act (1939) - Stops government workers from doing politics on the job."
]

# Selection sidebar
with st.sidebar:
    st.header("Choose Your Project")
    selected_act = st.selectbox("Pick an Act:", [a.split(" - ")[0] for a in acts], key="act_select")
    if selected_act:
        st.session_state.act = selected_act
    
    project_types = ["A paragraph describing a scenario", "A comic strip of a scenario", "A skit showing a scenario"]
    selected_type = st.selectbox("What do you want to create?", project_types, key="type_select")
    if selected_type:
        st.session_state.project_type = selected_type
    
    if st.button("Start Creating!"):
        if st.session_state.act and st.session_state.project_type:
            # Set system prompt
            act_desc = next(desc for act, desc in zip([a.split(" - ")[0] for a in acts], [a.split(" - ")[1] for a in acts]) if act == st.session_state.act)
            type_map = {
                "A paragraph describing a scenario": "paragraph",
                "A comic strip of a scenario": "comic strip",
                "A skit showing a scenario": "skit"
            }
            proj_type = type_map[selected_type]
            st.session_state.system_prompt = f"""You are a kind and patient AI teacher assistant for special needs students in a general education classroom. 
            Your goal is to help the student create a simple, fun {proj_type} about a scenario under the {st.session_state.act}: {act_desc}.
            
            Rules:
            - Keep everything simple, positive, and short.
            - Always ask one question at a time, with 2-4 simple options (e.g., A, B, C) for the student to choose from.
            - Use the student's choices to build the project step by step.
            - For paragraphs: Aim for 4-6 sentences.
            - For comic strips: Create 3-4 panels with simple text descriptions (no images yet).
            - For skits: Write a short script with 2-3 characters and simple dialogue.
            - End by generating the full project once enough info is gathered.
            - If the student says "done" or similar, generate the final output.
            - Be encouraging: "Great choice!" or "That's a cool idea!"
            
            Start by asking: 'What's a fun scenario you can think of for this act? Like, who is involved? (A) A president and vice president, (B) Government workers at a party, (C) Friends talking about elections, (D) Something else - tell me!'"""

            st.session_state.gathering_info = True
            st.session_state.chat_history = []
            st.session_state.final_project = None
            st.rerun()
        else:
            st.warning("Please select both an act and project type first!")

# Main chat interface
if st.session_state.act and st.session_state.project_type and st.session_state.system_prompt:
    st.header(f"Creating a {st.session_state.project_type.lower()} about the {st.session_state.act}")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # If gathering info, chat mode
    if st.session_state.gathering_info:
        # User input
        if prompt := st.chat_input("Type your answer here (or say 'done' when ready for the final project!):"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    messages = [{"role": "system", "content": st.session_state.system_prompt}] + st.session_state.chat_history
                    response = client.chat.completions.create(
                        model=""grok-4-latest"",  # Use appropriate xAI model
                        messages=messages,
                        max_tokens=300,
                        temperature=0.7
                    )
                    ai_reply = response.choices[0].message.content
                    st.markdown(ai_reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
                    
                    # Check if done (simple keyword check; improve with better logic if needed)
                    if any(word in prompt.lower() for word in ["done", "finish", "ready"]):
                        st.session_state.gathering_info = False
                        # Trigger final generation in next rerun
                        st.rerun()
    
    # Final project generation
    elif not st.session_state.final_project:
        with st.spinner("Putting it all together!"):
            messages = [{"role": "system", "content": st.session_state.system_prompt + "\n\nNow, using all the info from our chat, generate the final project."}] + st.session_state.chat_history
            response = client.chat.completions.create(
                model=""grok-4-latest"",
                messages=messages,
                max_tokens=800,
                temperature=0.5
            )
            final_output = response.choices[0].message.content
            st.session_state.final_project = final_output
        
        st.subheader("Your Finished Project! 🎉")
        st.markdown(st.session_state.final_project)
        
        # Download button
        st.download_button(
            label="Download as Text File",
            data=st.session_state.final_project,
            file_name=f"{st.session_state.act}_{st.session_state.project_type.lower().replace(' ', '_')}.txt",
            mime="text/plain"
        )
        
        # Reset button
        if st.button("Create Another Project"):
            for key in ["act", "project_type", "chat_history", "system_prompt", "gathering_info", "final_project"]:
                del st.session_state[key]
            st.rerun()
else:
    st.info("👈 Select an act and project type in the sidebar to get started!")

# Footer
st.markdown("---")
st.caption("Powered by xAI's Grok API. For teachers: Deploy on Streamlit Cloud and add your API key in secrets.")
