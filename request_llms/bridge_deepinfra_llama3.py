# encoding: utf-8
# @Time   : 2023/12/21
# @Author : Spike
# @Descr   :
import json
import re
import os
import time
import logging
from openai import OpenAI
from toolbox import get_conf, update_ui, update_ui_lastest_msg, have_any_recent_upload_image_files, trimmed_format_exc

proxies, TIMEOUT_SECONDS, MAX_RETRY = get_conf('proxies', 'TIMEOUT_SECONDS', 'MAX_RETRY')
timeout_bot_msg = '[Local Message] Request timeout. Network error. Please check proxy settings in config.py.' + \
                  '网络错误，检查代理服务器是否可用，以及代理设置的格式是否正确，格式须是[协议]://[地址]:[端口]，缺一不可。'

DEEPINFRA_API_KEY=get_conf("DEEPINFRA_API_KEY")

genai = OpenAI(
    api_key = DEEPINFRA_API_KEY,
    base_url ="https://api.deepinfra.com/v1/openai",
)
MODEL_NAME = 'meta-llama/Meta-Llama-3-70B-Instruct'

def generate_message_payload(history, inputs):
    '''
    chatbot is a list of (inputs, response)
    return a list that is used by gemini
    >>> messages = [{'role':'user', 'parts': ['hello']}]
    >>> response = model.generate_content(messages) # "Hello, how can I help"
    >>> messages.append(response.candidates[0].content)
    >>> messages.append({'role':'user', 'parts': ['How does quantum physics work?']})
    >>> response = model.generate_content(messages)
    '''
    
    ls_history = [i for i in history]
    ls_history.append(inputs)
    messages = []
    for i in range(len(ls_history)):
        if i % 2 == 0:
            messages.append({'role':'user', 'content': ls_history[i]})
        else:
            messages.append({'role':'assistant', 'content': ls_history[i]})
    return messages

def predict_no_ui_long_connection(inputs, llm_kwargs, history=[], sys_prompt="", observe_window=None,
                                  console_slience=False):
    # 检查API_KEY
    if get_conf("DEEPINFRA_API_KEY") == "":
        raise ValueError(f"请配置 DEEPINFRA_API_KEY")
    
    # prepare the input
    messages = generate_message_payload(history, inputs)
    response = genai.chat.completions.create(messages=messages,model=MODEL_NAME)
    return response.text


def predict(inputs, llm_kwargs, plugin_kwargs, chatbot, history=[], system_prompt='', stream=True, additional_fn=None):
    
    chatbot.append((inputs, ""))
    # 检查API_KEY
    if get_conf("DEEPINFRA_API_KEY") == "":
        raise ValueError(f"请配置 DEEPINFRA_API_KEY")
        return None
    
    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)

    # prepare the input 
    messages = generate_message_payload(history, inputs)
    # 开始接收回复
    print(messages)
    response_iter = genai.chat.completions.create(messages=messages, model=MODEL_NAME, stream=True)
    response_text = ''
    for n,response in enumerate(response_iter):
        if not response.choices[0].delta.content:
            continue
        response_text += response.choices[0].delta.content
        chatbot[-1] = (inputs, response_text)
        if n % 10 == 0:
            yield from update_ui(chatbot=chatbot, history=history)

    raw_input = inputs
    logging.info(f'{MODEL_NAME} [raw_input] {raw_input}')
    logging.info(f'{MODEL_NAME} [response] {response_text}')
    # 总结输出
    if response_text == f"[Local Message] 等待{MODEL_NAME}响应中 ...":
        response_text = f"[Local Message] {MODEL_NAME}响应异常 ..."
    history.extend([inputs, response_text])
    yield from update_ui(chatbot=chatbot, history=history)

