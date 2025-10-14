import os
import json
import requests
import concurrent.futures
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import PageContent
# import threading


# --- Softcodix Gemini Query ---
def query_gemini(user_query, website_content, services, timeout=4):
    """Ask Gemini to answer user query based on trax9 website data"""
    try:
        prompt = f"""
        You are a helpful assistant for **trax9**.
        You are a friendly **sales agent** for trax9.

        📝 RULES:
        - Always reply in same language as user query.
        - Always reply in same language as user query(English and Roman Urdu).
        - If language is "urdu", reply in **Roman Urdu** (English alphabets only).
        - If language is "English", reply in **English** (reply in same language as user query).
        - Keep answers short (3-5 lines).
        - Be professional but friendly, like chatting on WhatsApp.
        - Do NOT always start with greetings.
        - If query is about services, explain briefly with 2-3 bullet points.
        - End with a small call-to-action (e.g., "Would you like more details?" or "Shall I connect you to our team?").

        Company Info:
        {website_content}

        Our Services:
        {services}  

        User asked: {user_query}
        """

        GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", None)
        if not GEMINI_API_KEY:
            return "⚠️ Gemini API key not configured."

       # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            return f"⚠️ Gemini error: {response.status_code}"

    except Exception as e:
        return f"⚠️ Gemini exception: {str(e)}"


# --- Timeout wrapper (max 4s) ---
def query_with_timeout(user_query, website_content, services, timeout=4):
    """Run Gemini query but fallback if slow"""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(query_gemini, user_query, website_content, services, timeout)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return "⏳ Server busy hai, please try again shortly."


# --- Main Smart Handler ---
def smart_query_handler(user_query):
    """Main trax9 chatbot handler"""
    # 🔎 First check DB
    db_result = PageContent.objects.filter(content__icontains=user_query)
    if db_result.exists():
        snippet = db_result.first().content[:400]
        return f"🔍 I found this info:\n{snippet}"


    # 🔎 Collect data for context
    # website_content = "Softcodix is an IT solutions company providing AI, automation, and custom development."
    # services = "- AI Chatbots\n- Web & Mobile Development\n- Business Automation\n- Cloud & API Integrations"
    

# 🔎 Collect data for context
    website_content = (
        "Trax9 is a creative digital agency offering complete web solutions — from design to development. "
        "We specialize in web development, mobile app creation, digital marketing, and SEO strategies to help businesses grow online. "
        "Our team combines technology, creativity, and marketing expertise to deliver impactful digital experiences."
    )

    services = (
        "- Website Development\n"
        "- Mobile App Development\n"
        "- SEO (Search Engine Optimization)\n"
        "- Digital Marketing & Advertising\n"
        "- Logo & Graphic Designing\n"
        "- Branding & Content Creation\n"
        "- Video Animation & Motion Graphics"
    )


    

    # 🔎 Use Gemini with timeout
    return query_with_timeout(user_query, website_content, services, timeout=4)


# --- Webhook for Dialogflow ---
# @csrf_exempt
# def dialogflow_webhook(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "Invalid request method"}, status=405)

#     body = json.loads(request.body.decode("utf-8"))
#     user_query = body.get("queryResult", {}).get("queryText", "")
#     intent_name = body.get("queryResult", {}).get("intent", {}).get("displayName", "")

#     print(f"[Webhook] User Query: {user_query}")
#     print(f"[Webhook] Intent: {intent_name}")

    
#     if intent_name == "LLMQueryIntent":
#         reply = smart_query_handler(user_query)
#         return JsonResponse({"fulfillmentText": reply})
    
    
#     elif intent_name == "Default Fallback Intent":
#         # Gemini / Smart handler se response lo
#         reply = smart_query_handler(user_query)
#         return JsonResponse({"fulfillmentText": reply})


#    # return JsonResponse({"fulfillmentText": "⚠️ Intent not handled."})

# # ❓ Unknown input
#     else:
#         reply = smart_query_handler(user_query)
        
#         response_payload = {
#             "fulfillmentMessages": [
#                 {"text": {"text": [reply]}}
#             ]
#         }

#         return JsonResponse({"fulfillmentText": reply})


@csrf_exempt
def dialogflow_webhook(request):
    print("\n[DEBUG] 🔹 Incoming webhook request received")

    if request.method != "POST":
        print("[ERROR] ❌ Invalid request method:", request.method)
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        print("[DEBUG] 📨 Raw request body loaded successfully")
    except Exception as e:
        print("[ERROR] ❌ Failed to parse JSON body:", str(e))
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    # Extract query and intent info
    user_query = body.get("queryResult", {}).get("queryText", "")
    intent_name = body.get("queryResult", {}).get("intent", {}).get("displayName", "")

    print(f"[DEBUG] 🗣 User Query: {user_query}")
    print(f"[DEBUG] 🎯 Intent Name: {intent_name}")

    try:
        if intent_name == "LLMQueryIntent":
            print("[DEBUG] 🤖 Handling LLMQueryIntent...")
            reply = smart_query_handler(user_query)
            print(f"[DEBUG] ✅ LLMQueryIntent Reply: {reply}")
            return JsonResponse({"fulfillmentText": reply})

        elif intent_name == "Default Fallback Intent":
            print("[DEBUG] 🧠 Handling Default Fallback Intent...")
            reply = smart_query_handler(user_query)
            print(f"[DEBUG] ✅ Default Fallback Reply: {reply}")
            return JsonResponse({"fulfillmentText": reply})

        else:
            print("[DEBUG] ⚙️ Unknown or Custom Intent Handling...")
            reply = smart_query_handler(user_query)
            print(f"[DEBUG] ✅ Custom Intent Reply: {reply}")

            response_payload = {
                "fulfillmentMessages": [
                    {"text": {"text": [reply]}}
                ]
            }
            print("[DEBUG] 📤 Response payload prepared successfully")
            return JsonResponse(response_payload)

    except Exception as e:
        print("[ERROR] ❌ Exception in intent handling:", str(e))
        return JsonResponse({"fulfillmentText": "An error occurred while processing your request."}, status=500)

