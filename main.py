import json
import os

import streamlit as st

# which API?
# gemini -> free access for some llms under 50 RPM.

# some docs: https://ai.google.dev/gemini-api/docs

# calling gemini api
import google.generativeai as genai
import random

st.title("Ask LLM Flowchart")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
llm_list = ["gemini-1.5-flash-8b", "gemini-1.5-flash", "gemini-2.0-flash-exp"]
model = genai.GenerativeModel(random.choice(llm_list))
big_model = genai.GenerativeModel("gemini-1.5-pro")

# Initialization
def initialize_field(field_name, value=None):
    if field_name not in st.session_state:
        st.session_state[field_name] = value

initialize_field("clarifying_questions_list", [])
initialize_field("answers_list", [])
initialize_field("options_list", [])
initialize_field("answer", "")
initialize_field("answer_ready", False)

MAX_NUMBER_QUESTIONS = 3

# clear button
def clear():
    for key in st.session_state.keys():
        del st.session_state[key]

# step one: ask the first question
# only ask if option_one is not in session state
#if not st.session_state.clarifying_questions_list:
#    
#    st.session_state.clarifying_questions_list[0] = question
# else:
#    question = st.session_state.clarifying_questions_list[0]"""
question = st.text_input("Your question", "What are some nearby restaurants? I am in Brooklyn.", on_change=clear)
#st.write(question)

# TODO: this will be a loop
for round in range(MAX_NUMBER_QUESTIONS):
    if round > len(st.session_state.answers_list):
        continue
    
    # display all clarifying questins and their answers
    if not st.session_state.clarifying_questions_list:
        template = (
            f"Here is a question I received from a user: '{question}'. "
            "What is one question I can ask to clarify the request? " 
            "Respond just with a single question, no extra explanations."
        )
        clarifying_question = model.generate_content(template).text
        st.session_state.clarifying_questions_list.append(clarifying_question)  # todo: move this to after the user chooses an option
    elif len(st.session_state.clarifying_questions_list) == round:
        question_list = "\n".join(st.session_state.clarifying_questions_list)
        template = (
            f"Here is I received from a user: '{question}'.  "
            "I already asked a number of clarifying questions to understand it better:"
            + question_list + 
            "What other clarifying question should I ask? "
            "Respond with just a single question, no extra explanations."
        )
        clarifying_question = model.generate_content(template).text
        st.session_state.clarifying_questions_list.append(clarifying_question)
    else:    
        clarifying_question = st.session_state.clarifying_questions_list[round]
    st.write(clarifying_question)

    follow_up = (
        f"Given that the user asked {question}, and that we are asking the clarifying question {clarifying_question},"
        f" what are some reasonable answers to the clarifying question? Only include as many answer options as it make sense, don't go crazy."
        "Please respond as a JSON array of strings, without extra explanation"
    )
    def drop_tickticktick(text):
        text = text.strip()
        if text.startswith("```"):
            text = text[text.find("\n"):]
        if text.endswith("```"):
            text = text[:-len("```")]
        return text

    if len(st.session_state.options_list) <= round:
        response = model.generate_content(follow_up)
        options = drop_tickticktick(response.text)
        MAX_NUMBER_OPTIONS = 5
        options_list = json.loads(options)[:MAX_NUMBER_OPTIONS]
        st.session_state.options_list.append(options_list)
    else:
        options_list = st.session_state.options_list[round]
    
    # display
    # https://docs.streamlit.io/develop/api-reference/widgets/st.button

    columns = st.columns(len(options_list))
    option_chosen = None
    # disabled = (len(st.session_state.answers_list) > round)
    # TODO: fix if the user presses the buttons in the wrong order.
    for column, option in zip(columns, options_list):
        with column:
            button_type = 'secondary'
            if len(st.session_state.answers_list) > round and option == st.session_state.answers_list[round]:
                button_type = 'primary'
            if st.button(option, use_container_width=True, type=button_type):
                if len(st.session_state.answers_list) <= round:  # not disabled
                    # this is happening on click
                    option_chosen = option
                    st.session_state.answers_list.append(option)
                    st.rerun()  # need to refresh to disable the buttons

if option_chosen is not None:
    st.write(f"User chose option: {option_chosen}")

# given clarifying questions and answers, get gemini to produce a final response

# st.session_state.clarifying_questions_list
# st.session_state.answers_list
if len(st.session_state.answers_list) == MAX_NUMBER_QUESTIONS and not st.session_state.answer_ready:
    clarifying_questions = "\n".join(st.session_state.clarifying_questions_list)
    user_answers = "\n".join(st.session_state.answers_list)
    final_template = (
        f"I got this question from the user {question}, "
        f"Based on the clarifying questions {clarifying_questions} and "
        f"user answers {user_answers} can you proivide a final answer?"
    )
    response = big_model.generate_content(final_template, stream=True)
    def data_generator():
        for chunk in response:
            a = chunk.text
            st.session_state.answer += a
            yield a
        st.session_state.answer_ready = True
    st.write_stream(data_generator)
    
elif st.session_state.answer_ready:
    st.write(st.session_state.answer)

# https://github.com/google-gemini/generative-ai-python/blob/5a3ba73b363f08b7feb319791f2db6c1d6b00c6f/google/generativeai/types/generation_types.py#L629

if st.button("Clear"):
    clear()
    st.rerun()