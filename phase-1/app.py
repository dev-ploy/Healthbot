# --- YouTube video search via SerpAPI ---
def serpapi_youtube_search(query):
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        return []
    try:
        import serpapi
        client = serpapi.Client(api_key=serpapi_key)
        results = client.search({
            "engine": "youtube",
            "search_query": query,
            "num": 3
        })
        video_results = results.get("video_results", [])
        videos = []
        for v in video_results:
            title = v.get("title", "No title")
            link = v.get("link", "")
            thumbnail = v.get("thumbnail", "")
            videos.append({"title": title, "link": link, "thumbnail": thumbnail})
        return videos
    except Exception:
        return []
# =========================
# 🖥️ SIMPLE STREAMLIT UI WITH GROQ LLM
# =========================

from dotenv import load_dotenv
import os
load_dotenv()
import websocket

import streamlit as st
import requests

def groq_llm_answer(question):
    """Call Groq LLM and ask for an answer without references."""
    try:
        from groq import Groq
        import os
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "GROQ_API_KEY not set."
        client = Groq(api_key=api_key)
        prompt = (
            "You are a clinical assistant. Answer the following question in a structured, evidence-based way. "
            "Do not include references or sources in your answer.\n\nQuestion: " + question
        )
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"


def get_hospitals_serpapi(location="Bangalore"):
    """Fetch hospitals near a location using SerpAPI's Google Maps API."""
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        return [], "SERPAPI_API_KEY not set."
    params = {
        "engine": "google_maps",
        "q": f"hospitals near {location}",
        "type": "search",
        "api_key": serpapi_key
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
        data = resp.json()
        results = data.get("local_results", [])
        # Attach raw data for debugging if no results
        debug_data = data
        hospitals = []
        locations = []
        for r in results:
            name = r.get("title", "Unnamed Hospital")
            address = r.get("address", "")
            lat = r.get("gps_coordinates", {}).get("latitude")
            lng = r.get("gps_coordinates", {}).get("longitude")
            hospitals.append(f"{name} ({address})")
            if lat and lng:
                locations.append({"name": name, "lat": lat, "lng": lng})
        if not hospitals:
            # Return debug_data for UI debug display
            return [], {"msg": "No hospitals found.", "debug": debug_data}
        return hospitals[:20], locations[:20]
    except Exception as e:
        return [], f"Error fetching hospitals: {e}"

# --- Web search fallback for medical Q&A ---
def serpapi_web_search(query):
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        return "SERPAPI_API_KEY not set."
    params = {
        "engine": "google",
        "q": query,
        "api_key": serpapi_key,
        "num": 5
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
        data = resp.json()
        results = data.get("organic_results", [])
        web_results = []
        for r in results:
            title = r.get("title", "No title")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            web_results.append({"title": title, "snippet": snippet, "link": link})
        return web_results
    except Exception as e:
        return f"Error fetching web results: {e}"

st.set_page_config(page_title="🩺 Healthbot - Medical Assistant", layout="wide")

# --- Branding and Header ---
st.markdown("""
<div style='display: flex; align-items: center; gap: 1rem;'>
    <img src='https://img.icons8.com/fluency/48/000000/hospital-3.png' width='48'/>
    <h1 style='margin-bottom: 0;'>Healthbot</h1>
</div>
<h4 style='margin-top: 0;'>AI Medical Assistant </h4>
<hr style='margin-bottom: 1.5rem;'>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Medical Q&A",
    "🏥 Hospital Finder",
    "📄 Prescription Upload",
    "💊 Medication Reminders",
    "📁 Health Records",
    "⚠️ Drug Interaction Check",
    "🛠️ Skills (Agentic Demo)"
])

# --- Medical Q&A Tab ---
with tab1:
    # Only show the input bar with a visible label for accessibility
    question = st.text_input("Ask a medical question", "", key="qa_input_main")
    if st.button("Get Answer", key="qa_btn_main"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                answer = groq_llm_answer(question)
            if answer and answer.startswith("Error"):
                st.error(answer)
            else:
                st.markdown("**Answer:**")
                st.write(answer)
                # Always show latest web results for up-to-date info
                with st.spinner("Fetching latest web results..."):
                    web_results = serpapi_web_search(question)
                if isinstance(web_results, str):
                    st.info(web_results)
                elif web_results:
                    st.markdown("**Web Results:**")
                    for r in web_results:
                        st.markdown(f"[{r['title']}]({r['link']})\n> {r['snippet']}")
                else:
                    st.info("No recent web results found.")

                # --- Related Videos (YouTube via SerpAPI) ---
                with st.spinner("Searching for related videos..."):
                    videos = serpapi_youtube_search(question)
                if videos:
                    st.markdown("**Related Videos:**")
                    for v in videos:
                        st.markdown(f"<a href='{v['link']}' target='_blank'><img src='{v['thumbnail']}' width='200'/><br>{v['title']}</a>", unsafe_allow_html=True)
                # Only show section if videos found (per user request)

# --- Agentic Skills ---
def skill_symptom_checker(symptom):
    # Minimal demo: just echo
    return f"(Skill) You entered: {symptom}. For real triage, integrate with a symptom checker API."

def skill_drug_info(drug):
    # Minimal demo: just echo
    return f"(Skill) Info for {drug}: For real info, integrate with a drug database API."

def skill_health_tip():
    # Minimal demo: random tip
    import random
    tips = [
        "Stay hydrated and exercise regularly.",
        "Wash your hands frequently.",
        "Get enough sleep for better immunity.",
        "Eat a balanced diet rich in fruits and vegetables."
    ]
    return random.choice(tips)

def agentic_router(user_input):
    # Minimal intent router
        # Try WebSocket for echo and tip
        ws_result = ws_agentic_skill(user_input)
        if ws_result:
            return ws_result
        if "symptom" in user_input.lower():
            return skill_symptom_checker(user_input)
        elif "drug" in user_input.lower():
            return skill_drug_info(user_input)
        elif "tip" in user_input.lower():
            return skill_health_tip()
        else:
            return "(Agent) No matching skill found. Try mentioning 'symptom', 'drug', or 'tip'."
    # --- Reflection/Self-Correction Wrapper ---
def reflection_agent(user_input):
        response = agentic_router(user_input)
        # Minimal reflection: check for generic or error responses
        if not response or "no matching skill" in response.lower() or "error" in response.lower():
            # Self-correct: try to rephrase or provide a fallback
            if "symptom" in user_input.lower():
                return "(Reflection) Sorry, I couldn't process your symptom. Please try rephrasing or provide more details."
            elif "drug" in user_input.lower():
                return "(Reflection) Sorry, I couldn't find information on that drug. Please check the spelling or try another."
            elif "tip" in user_input.lower():
                return skill_health_tip()
            else:
                return "(Reflection) Sorry, I couldn't understand your request. Please try again."
        return response

# --- Minimal WebSocket client for agentic skills ---
# --- Minimal WebSocket client for agentic skills ---
def ws_agentic_skill(message):
    try:
        import websocket
        ws = websocket.create_connection("ws://localhost:8000/ws/skill", timeout=2)
        ws.send(message)
        result = ws.recv()
        ws.close()
        return f"(WebSocket) {result}"
    except Exception:
        return None

# --- Skills Tab (Agentic Demo) ---
with tab7:
    st.subheader("Agentic Skills Demo")
    st.markdown("Available skills: symptom checker, drug info, health tip generator.")
    skill_input = st.text_input("Type your request (e.g., 'symptom headache', 'drug aspirin', 'tip')", "", key="skill_input_1")
    if st.button("Run Skill", key="skill_btn_1"):
        if not skill_input.strip():
            st.warning("Please enter a request.")
        else:
            result = agentic_router(skill_input)
            st.info(result)
        st.subheader("Agentic Skills Demo (with Reflection)")
        st.markdown("Available skills: symptom checker, drug info, health tip generator. Now with self-correction!")
        skill_input = st.text_input("Type your request (e.g., 'symptom headache', 'drug aspirin', 'tip')", "", key="skill_input_2")
        if st.button("Run Skill", key="skill_btn_2"):
            if not skill_input.strip():
                st.warning("Please enter a request.")
            else:
                result = reflection_agent(skill_input)
                st.info(result)
import datetime
import urllib.parse
# --- Medication Reminders Tab ---
with tab4:
    st.subheader("Set a Medication Reminder (Minimal Demo)")
    med_name = st.text_input("Medication Name", "", key="reminder_med")
    med_time = st.time_input("Time to take medication", datetime.time(9, 0), key="reminder_time")
    if st.button("Save Reminder", key="reminder_btn"):
        if not med_name.strip():
            st.warning("Please enter a medication name.")
        else:
            st.success(f"Reminder set for {med_name} at {med_time.strftime('%H:%M')}. (Demo: No notifications)")

# --- Health Records Tab ---
with tab5:
    st.subheader("Upload and View Health Records (Minimal Demo)")
    record_file = st.file_uploader("Upload health record (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"], key="record_upload")
    if record_file is not None:
        st.success(f"Uploaded: {record_file.name}")
        if record_file.type.startswith("image"):
            st.image(record_file, caption=record_file.name, use_column_width=True)
        elif record_file.type == "application/pdf":
            st.info("PDF preview not supported in minimal demo.")


# --- Drug Interaction Checker Tab (with RxNav API) ---
def get_rxnorm_id(drug_name):
    # Get RxNorm ID for a drug name
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={urllib.parse.quote(drug_name)}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        rxcui = data.get("idGroup", {}).get("rxnormId", [])
        return rxcui[0] if rxcui else None
    except Exception:
        return None

def check_interactions(rxcui_list):
    # Check interactions for a list of RxNorm IDs
    if len(rxcui_list) < 2:
        return "Enter at least two valid drugs for interaction check."
    ids = "+".join(rxcui_list)
    url = f"https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis={ids}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        interactions = []
        groups = data.get("fullInteractionTypeGroup", [])
        for group in groups:
            for itype in group.get("fullInteractionType", []):
                for pair in itype.get("interactionPair", []):
                    desc = pair.get("description", "")
                    drugs = [d.get("name", "") for d in itype.get("minConcept", [])]
                    interactions.append(f"{' + '.join(drugs)}: {desc}")
        if interactions:
            return interactions
        else:
            return "No known interactions found."
    except Exception:
        return "Error checking interactions."

with tab6:
    st.subheader("Check for Drug Interactions (Powered by RxNav API)")
    drugs = st.text_area("Enter a list of medications (comma separated)", "", key="interaction_input")
    if st.button("Check Interactions", key="interaction_btn"):
        if not drugs.strip():
            st.warning("Please enter at least one medication.")
        else:
            drug_list = [d.strip() for d in drugs.split(",") if d.strip()]
            rxcui_list = [get_rxnorm_id(d) for d in drug_list]
            if None in rxcui_list:
                st.warning("One or more drugs could not be recognized. Please check spelling.")
            else:
                with st.spinner("Checking interactions..."):
                    result = check_interactions(rxcui_list)
                if isinstance(result, list):
                    st.markdown("**Interactions found:**")
                    for r in result:
                        st.write(r)
                else:
                    st.info(result)
from PIL import Image
import easyocr
with tab3:
    st.subheader("Upload a prescription for analysis")
    uploaded_file = st.file_uploader("Upload prescription image (jpg, png)", type=["jpg", "jpeg", "png"], key="presc_upload")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Prescription", use_column_width=True)
        with st.spinner("Extracting text from image..."):
            reader = easyocr.Reader(['en'], gpu=False)
            extracted = reader.readtext(image)
            extracted_text = "\n".join([item[1] for item in extracted])
        if extracted_text.strip():
            st.markdown("**Extracted Text:**")
            st.code(extracted_text)
            # Optionally, allow user to query or forward to doctor
            st.markdown("---")
            st.subheader("Ask a question about this prescription")
            presc_query = st.text_input("Your question about the prescription", "", key="presc_query")
            if st.button("Get Answer", key="presc_query_btn"):
                if not presc_query.strip():
                    st.warning("Please enter a question.")
                else:
                    with st.spinner("Thinking..."):
                        # Use LLM with prescription context
                        context_prompt = f"Prescription text: {extracted_text}\n\nUser question: {presc_query}"
                        answer = groq_llm_answer(context_prompt)
                    if answer and isinstance(answer, str) and answer.startswith("Error"):
                        st.error(answer)
                    else:
                        st.markdown("**LLM Answer:**")
                        st.write(answer)
        else:
            st.warning("No text could be extracted from the image. Please try a clearer photo.")

with tab1:
    st.subheader("Ask a medical question")
    user_question = st.text_input("Your question", "", key="qa_input_presc")
    if st.button("Get Answer", key="qa_btn_presc"):
        if not user_question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                answer = groq_llm_answer(user_question)
            if answer.startswith("Error"):
                st.error(answer)
            else:
                st.markdown("**Answer:**")
                st.write(answer)
                # Always show latest web results for up-to-date info
                with st.spinner("Fetching latest web results..."):
                    web_results = serpapi_web_search(user_question)
                if isinstance(web_results, str):
                    st.warning(web_results)
                elif web_results:
                    st.markdown("**Latest Web Results:**")
                    for r in web_results:
                        st.markdown(f"- [{r['title']}]({r['link']})<br><span style='color:#888'>{r['snippet']}</span>", unsafe_allow_html=True)
                else:
                    st.info("No recent web results found.")

with tab2:
    st.subheader("Find hospitals near a location")
    location = st.text_input("Location", "Bangalore", key="hosp_input")
    if st.button("Find Hospitals", key="hosp_btn"):
        if not location.strip():
            st.warning("Please enter a location.")
        else:
            with st.spinner(f"Fetching hospitals near {location} from Google Maps (SerpAPI)..."):
                hospitals, locations = get_hospitals_serpapi(location)
            if isinstance(hospitals, str):
                st.error(hospitals)
            elif not hospitals:
                # If debug info is present, show it
                if isinstance(locations, dict) and "debug" in locations:
                    st.warning("No hospitals found. Showing raw SerpAPI response for debugging:")
                    st.json(locations["debug"])
                else:
                    st.warning("No hospitals found.")
            else:
                st.markdown(f"**Hospitals near {location}:**")
                for h in hospitals:
                    st.write("- ", h)
                # Show map if locations available
                if locations:
                    import pandas as pd
                    df = pd.DataFrame(locations)
                    st.map(df.rename(columns={"lat": "latitude", "lng": "longitude"}))

 # --- Footer ---
st.markdown("""
<hr>
<div style='text-align: center; color: #888; font-size: 0.9em;'>
    &copy; 2026 Healthbot | Powered by Groq LLM & SerpAPI | <a href='https://github.com/dev-ploy/Healthbot' target='_blank'>GitHub</a>
</div>
""", unsafe_allow_html=True)


