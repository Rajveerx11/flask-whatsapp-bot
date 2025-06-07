from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from flask_session import Session
import mysql.connector
import redis

app = Flask(__name__)

# Configure Redis session
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.Redis(host='localhost', port=6379)
app.config["SECRET_KEY"] = "super-secret-key"  # Change in production
Session(app)

# MySQL Configuration
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rajveer@8685",  # Change this
    database="Social_Records"  # Change this
)
cursor = conn.cursor(dictionary=True)

# Department keyword mapping
department_keywords = {
    "garbage": ("Solid Waste Management", "https://septictank.solapurcorporation.org/Septic_Tank_Application.aspx"),
    "trash": ("Solid Waste Management", "https://septictank.solapurcorporation.org/Septic_Tank_Application.aspx"),
    "electricity": ("Electric Department", "https://smc.gov.in/complaints/electric"),
    "light": ("Electric Department", "https://smc.gov.in/complaints/electric"),
    "road": ("Engineering Department", "https://smc.gov.in/complaints/roads"),
    "sewage": ("Drainage Department", "http://dcms.solapurcorporation.org/"),
    "water": ("Water Supply", "https://tcms.solapurcorporation.org/"),
    "tree": ("Garden Department", "https://smc.gov.in/complaints/garden"),
    "animal": ("Veterinary", "https://smc.gov.in/complaints/animal"),
    "illegal": ("Encroachment", "https://smc.gov.in/complaints/encroachment"),
    "slum": ("UCD (NULM)", "https://smc.gov.in/complaints/slum"),
    "market": ("Market Department", "https://smc.gov.in/complaints/market"),
    "property": ("Tax Department", "https://smccity.solapurcorporation.org/noc_online.aspx")
}

# Table mapping
table_map = {
    "1": "married_status",
    "2": "caste_status",
    "3": "property_status",
    "4": "birth_status",
    "5": "death_status"
}

# Menus
app_menu = (
    "📋 *Application Status Services*\n"
    "1️⃣ Marriage Status\n"
    "2️⃣ Caste Certificate Status\n"
    "3️⃣ Property Tax Status\n"
    "4️⃣ Birth Certificate Status\n"
    "5️⃣ Death Certificate Status"
)

main_menu = (
    "👤 *Welcome to Digital SMC Services*\n"
    "What do you want to do?\n"
    "1️⃣ Check Application Status\n"
    "2️⃣ Register a Complaint"
)

# Format DB reply
def format_reply(table, data):
    if table == "married_status":
        return f"👤 Name: {data['name']}\n📍 Place: {data['place']}\n📄 Status: {data['status']}\n⏳ ETA: {data['estimated_time']}"
    elif table == "caste_status":
        return f"👤 Name: {data['name']}\n📍 Area: {data['place']}\n📄 Status: {data['status']}\n⏳ ETA: {data['estimated_time']}"
    elif table == "property_status":
        return f"👤 Name: {data['name']}\n🏠 Location: {data['property_location']}\n📄 Status: {data['status']}\n⏳ ETA: {data['estimated_time']}"
    elif table == "birth_status":
        dob = data['birth_date'].strftime("%d-%b-%Y") if data['birth_date'] else "N/A"
        return f"👶 Name: {data['name']}\n🎂 DOB: {dob}\n📄 Status: {data['status']}\n⏳ ETA: {data['estimated_time']}"
    elif table == "death_status":
        dod = data['death_date'].strftime("%d-%b-%Y") if data['death_date'] else "N/A"
        return f"🧎‍ Name: {data['name']}\n📅 Date: {dod}\n📄 Status: {data['status']}\n⏳ ETA: {data['estimated_time']}"
    return "❌ No record found."

@app.route("/bot", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip().lower()
    from_number = request.values.get("From")
    resp = MessagingResponse()

    if "stage" not in session:
        session["stage"] = "main"
        resp.message("👋 Hello!\n" + main_menu)
        return str(resp)

    stage = session["stage"]

    if stage == "main":
        if incoming_msg == "1":
            session["stage"] = "menu"
            resp.message("📄 You selected *Application Status*\n" + app_menu)
        elif incoming_msg == "2":
            session["stage"] = "complaint_intro"
            resp.message("📝 Please describe your complaint briefly.")
        else:
            resp.message("❗ Invalid option.\n" + main_menu)
        return str(resp)

    if stage == "complaint_intro":
        matched = False
        for keyword, (dept, url) in department_keywords.items():
            if keyword in incoming_msg:
                session["stage"] = "complaint_confirm"
                session["dept"] = dept
                session["url"] = url
                resp.message(f"🛠️ Your complaint seems to belong to:\n*Department:* {dept}\n🌐 Register here: {url}\n\nDo you want to continue and enter your full complaint? Reply with 'yes' or 'no'.")
                matched = True
                break
        if not matched:
            resp.message("❓ Sorry, we couldn't identify the department. Please try describing differently.")
        return str(resp)

    if stage == "complaint_confirm":
        if incoming_msg in ["yes", "y"]:
            session["stage"] = "complaint_final"
            resp.message("✍️ Please enter your full complaint now.")
        elif incoming_msg in ["no", "n"]:
            resp.message("🙏 Thank you for contacting us. Goodbye!")
            session.clear()
        else:
            resp.message("❓ Please reply with 'yes' or 'no'.")
        return str(resp)

    if stage == "complaint_final":
        resp.message("✅ Thank you for your complaint. Our team will contact you shortly.")
        session.clear()
        return str(resp)

    if stage == "menu":
        if incoming_msg in table_map:
            session["table"] = table_map[incoming_msg]
            session["stage"] = "ask_search_method"
            resp.message("🔍 Search by:\n👉 *ID* or *Name*?")
        else:
            resp.message("❗ Invalid option.\n" + app_menu)
        return str(resp)

    if stage == "ask_search_method":
        if incoming_msg == "id":
            session["stage"] = "awaiting_app_id"
            resp.message("📥 Enter your *Application ID*:")
        elif incoming_msg == "name":
            session["stage"] = "awaiting_name"
            resp.message("📥 Enter your *Full Name*:")
        else:
            resp.message("❗ Reply with 'id' or 'name'.")
        return str(resp)

    if stage == "awaiting_app_id":
        table = session["table"]
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE application_id = %s", (incoming_msg.upper(),))
            result = cursor.fetchone()
            if result:
                resp.message("✅ Application Details:\n" + format_reply(table, result) + "\n\n🔁 Want another service? (Yes/No)")
                session["stage"] = "awaiting_continue"
            else:
                resp.message("❌ No application found with that ID.")
        except Exception:
            resp.message("❌ Database error. Please try again.")
        return str(resp)

    if stage == "awaiting_name":
        table = session["table"]
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE name = %s", (incoming_msg.title(),))
            results = cursor.fetchall()
            if results:
                messages = [format_reply(table, row) for row in results]
                resp.message("\n\n".join(messages) + "\n\n🔁 Want another service? (Yes/No)")
                session["stage"] = "awaiting_continue"
            else:
                resp.message("❌ No applications found under that name.")
        except Exception:
            resp.message("❌ Database error. Please try again.")
        return str(resp)

    if stage == "awaiting_continue":
        if incoming_msg in ["yes", "y"]:
            session["stage"] = "main"
            resp.message(main_menu)
        elif incoming_msg in ["no", "n"]:
            resp.message("🙏 Thank you for using Digital SMC ChatBot. Goodbye!")
            session.clear()
        else:
            resp.message("❓ Reply with *Yes* or *No*.")
        return str(resp)

    resp.message("❗ Something went wrong. Please type 'hi' to restart.")
    session.clear()
    return str(resp)

if __name__ == "__main__":
    print("🚀 WhatsApp bot running on http://127.0.0.1:5000")
    app.run(debug=True)
