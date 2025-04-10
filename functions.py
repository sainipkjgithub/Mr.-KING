import requests

import os

user_histories = {}

def clear_history():
  del user_histories[user_id] 
  
def sendAi_message(user_id,user_name, user_msg):
    url = "https://text.pollinations.ai/openai"
    headers = {"Content-Type": "application/json"}

    # अगर यूज़र पहली बार मैसेज भेज रहा है, तो उसकी हिस्ट्री इनिशियलाइज़ करें
    if user_id not in user_histories:
        user_histories[user_id] = []

    # नया मैसेज JSON फ़ॉर्मेट में हिस्ट्री में जोड़ें
    user_histories[user_id].append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_msg
            }
        ]
    })

    # API को भेजने के लिए JSON payload तैयार करें
    payload = {
        "model": "gpt-4",
        "system": f"""
You are Mr. King a UPSC Helper. Only answer UPSC related Questions. Don't answer any question which is not related to study.
Student Details:
Name: {user_name}
Telegram ID: {user_id}
        """,
        "messages": user_histories[user_id]  # यूज़र की पूरी हिस्ट्री भेजें
    }

    # API कॉल करें
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        result = response.json()
        assistant_msg = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        # असिस्टेंट का जवाब भी सही फ़ॉर्मेट में स्टोर करें
        user_histories[user_id].append({
            "role": "assistant",
            "content": assistant_msg
        })

        return assistant_msg
    else:
        return f"Error to connection you to ai assistant. Please try again later"
