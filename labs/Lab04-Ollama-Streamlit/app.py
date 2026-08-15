import ollama as client
import streamlit as st

def stream_data(stream):
     for chunk in stream:
        yield chunk['message']['content'] + ""

def main():
    st.title("Chat With LLaMA")

    if "llm_model" not in st.session_state:
        st.session_state["llm_model"] = "llama3.1:8b"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.chat(
                model=st.session_state["llm_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )

            response = st.write_stream(stream_data(stream))
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()