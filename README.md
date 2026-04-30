# LEAN ACQUISITION OS — STEP BY STEP BUILD GUIDE
### Partnership: Tamir Robertson + [Partner Name]
### Tamir Role: Tech Builder
### Partner Role: Strategy + Outreach + Sales
### Split: 50/50
### Start: Today

---

## BEFORE YOU START

```
This guide is Tamir's build guide only

Partner handles:
→ Lead finding
→ Email outreach
→ Sales calls
→ Client management

Tamir handles:
→ Every technical step
   in this guide
→ Automations
→ Website
→ Integrations
→ Systems

Time per day: 2 hours max
   (afternoons only)
   (mornings = Client System Pros)

Total build time: 7 days
Partner starts outreach: Day 8
First client target: Day 21
```

---

## PARTNERSHIP DOCUMENT FIRST

```
Before writing one line of code:

□ Open Google Docs
□ New document
□ Name it:
   "Lean Acquisition OS 
    Partner Agreement — 
    April 29 2026"

□ Paste and fill in:

---
Tamir Robertson + [Partner Name]
Partnership Agreement
Date: April 29 2026

Role — Tamir:
→ All technical builds
→ Automations + integrations
→ Website + systems
→ Maintenance + bug fixes

Role — [Partner]:
→ Lead outreach
→ Sales calls
→ Client management
→ Strategy decisions

Revenue Split:
→ 50/50 on all revenue
→ Paid monthly
→ After tool costs deducted

Tool costs deducted first:
→ Claude API ~$10/month
→ Make.com ~$9/month
→ Apollo ~$49/month
→ Other tools as added

Ownership:
→ Code owned jointly
→ Domain owned jointly
→ Neither can sell without
   other's consent

Exit clause:
→ 30 days written notice
→ Remaining partner buys out
   at agreed value
→ Or business winds down
   by mutual agreement
---

□ Both sign with name + date
□ Screenshot it
□ Both keep a copy

✅ Done when:
   Document signed by both
   Both have a copy saved
```

---

# DAY 1 — CORE INFRASTRUCTURE
## Tamir builds | Time: 2 hours

---

### STEP 1 — Gmail Account
```
Time: 15 minutes

□ Create new Gmail:
   hello@[partnerdomain].com
   OR use existing domain

□ Add professional signature:
   ---
   [Partner Name]
   Lean Acquisition OS
   [website when built]
   ---

□ Send 5 normal emails
   to friends or family
   (starts warming the account)

□ Share login with partner
   so he can access replies

✅ Done when:
   Gmail created
   Signature set
   Login shared with partner
```

---

### STEP 2 — HubSpot CRM
```
Time: 20 minutes

□ Go to hubspot.com
□ Click: Get started free
□ Sign up with new Gmail

□ Create pipeline:
   → Sales → Pipelines
   → Create pipeline
   → Name: LAO Acquisition

   → Add these 7 stages:
     1. Lead Found
     2. Outreach Sent
     3. Replied
     4. Call Booked
     5. Call Completed
     6. Proposal Sent
     7. Client Signed

□ Turn off all HubSpot
   email notifications

□ Share access with partner:
   → Settings → Users
   → Invite partner email

✅ Done when:
   Pipeline built
   Partner has access
```

---

### STEP 3 — Apollo.io
```
Time: 15 minutes

□ Go to apollo.io
□ Sign up free
□ Complete profile:
   → Name: [Partner Name]
   → Company: Lean Acquisition OS
   → Website: [when built]

□ Test first search:
   → Search → People
   → Filter:
     Job title: Agency Owner
     Location: United States
     Company size: 1-50
   → Save as: "Agency Owners USA"

□ Share login with partner
   (he uses this daily)

✅ Done when:
   Account created
   First search saved
   Partner has login
```

---

### STEP 4 — Calendly
```
Time: 15 minutes

□ Go to calendly.com
□ Sign up free
□ Connect Gmail calendar

□ Create event:
   → Name: 15-Min Discovery Call
   → Duration: 15 minutes
   → Location: Google Meet
   → Buffer: 15 min after each call

□ Set availability:
   → Monday-Thursday only
   → 10am-4pm partner timezone
   → Max 2 calls per day

□ Add 3 intake questions:
   Question 1:
   "What is your current
    monthly revenue?"
   (required)

   Question 2:
   "How are you currently
    getting new clients?"
   (required)

   Question 3:
   "What is your biggest
    challenge right now?"
   (required)

□ Copy booking link
□ Save it — goes in every email

✅ Done when:
   Link live
   Questions set
   Link saved
```

---

### STEP 5 — Telegram Bot
```
Time: 15 minutes

□ Open Telegram
□ Search: @BotFather
□ Send: /newbot
□ Name: LAO Alerts
□ Username: LAOAlertsBot
   (add numbers if taken)

□ Save immediately:
   → Bot API token
   → Looks like:
     7234567890:AAFxxx...

□ Get your Chat ID:
   → Search: @userinfobot
   → Start it
   → Copy your Chat ID

□ Save both:
   → Bot API token
   → Chat ID

□ Share both with partner
   so he gets alerts too

   To add partner:
   → He starts the bot
   → Get his Chat ID
   → Use both IDs in Make.com
     (send alerts to both)

✅ Done when:
   Bot created
   Both Chat IDs saved
   API token saved
```

---

### STEP 6 — Claude API
```
Time: 15 minutes

□ Go to console.anthropic.com
□ Create account
□ Verify email

□ Go to: API Keys
□ Click: Create Key
□ Name: LAO Main
□ Copy and save immediately
   (only shown once)

□ Go to: Billing
□ Add $10 credit
   (lasts 2-3 months at this scale)

□ Test the API:
   Open Terminal and paste
   (replace YOUR_KEY):

curl https://api.anthropic.com/v1/messages \
-H "x-api-key: YOUR_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "content-type: application/json" \
-d '{
  "model": "claude-3-haiku-20240307",
  "max_tokens": 100,
  "messages": [{
    "role": "user",
    "content": "Say: API working"
  }]
}'

→ Response received = ✅
→ Error = check API key

✅ Done when:
   Key saved
   $10 loaded
   Test returned response
```

---

### STEP 7 — Make.com
```
Time: 10 minutes

□ Go to make.com
□ Sign up free
□ Verify email
□ Skip all tutorials

□ Just create the account
□ Do not build anything yet
□ Building happens Day 5

✅ Done when:
   Account created
   Logged in
```

---

### STEP 8 — Google Sheets Tracker
```
Time: 30 minutes

□ Open Google Sheets
□ New spreadsheet
□ Name: LAO Master Tracker

□ TAB 1 — LEADS:
   Rename Sheet1 to: LEADS

   Column headers:
   A: First Name
   B: Last Name
   C: Company
   D: Email
   E: LinkedIn URL
   F: Website
   G: Niche
   H: Source
   I: Status
   J: Score (1-10)
   K: Last Contact Date
   L: Follow Up Date
   M: Email # Sent
   N: Notes
   O: (blank — Mailmeteor)

□ TAB 2 — METRICS:
   Add sheet → name: METRICS

   Headers:
   A: Date
   B: Leads Found
   C: Emails Sent
   D: Replies Received
   E: Reply Rate %
   F: Calls Booked
   G: Calls Completed
   H: Show Rate %
   I: Notes

□ TAB 3 — CLIENTS:
   Add sheet → name: CLIENTS

   Headers:
   A: Client Name
   B: Business Name
   C: Niche
   D: Start Date
   E: Monthly Fee
   F: Performance Fee
   G: Total Paid
   H: Renewal Date
   I: Status
   J: Case Study Y/N
   K: Notes

□ TAB 4 — REVENUE:
   Add sheet → name: REVENUE

   Headers:
   A: Month
   B: Gross Revenue
   C: Tool Costs
   D: Net Revenue
   E: Tamir 50%
   F: Partner 50%
   G: Notes

□ Format all tabs:
   → Bold headers
   → Dark background
   → White text
   → Freeze row 1

□ Share with partner:
   → Click Share
   → Add partner email
   → Editor access

✅ Done when:
   All 4 tabs built
   Partner has access
```

---

## DAY 1 CHECKLIST
```
□ Gmail created + warmed
□ HubSpot pipeline built
□ Apollo set up
□ Calendly link live
□ Telegram bot created
□ Claude API loaded + tested
□ Make.com account ready
□ Google Sheets tracker built
□ Partner has access to all tools

Infrastructure complete
Move to Day 2 tomorrow
```

---

# DAY 2 — EMAIL + OUTREACH SYSTEM
## Tamir builds | Time: 2 hours

---

### STEP 9 — Email Templates
```
Time: 45 minutes

□ Open Google Docs
□ New document
□ Name: LAO Email Templates

□ Write all 8 emails:
   Use the sequences from
   the Lean Acquisition OS doc
   Personalize with partner voice
   Partner should review + edit
   for his natural tone

   Tokens to use:
   {{First Name}}
   {{Company}}
   {{Niche}}

   Email 1 — Day 1  — Curiosity
   Email 2 — Day 3  — Value
   Email 3 — Day 7  — Direct Ask
   Email 4 — Day 14 — Soft
   Email 5 — Day 30 — Reactivation
   Email 6 — Day 45 — Check In
   Email 7 — Day 60 — Check In
   Email 8 — Day 90 — Final

□ Read each one out loud:
   → Sounds human? ✅
   → Under 100 words? ✅
   → One idea only? ✅
   → Clear CTA? ✅

□ Send doc to partner
   for voice review + edits

✅ Done when:
   All 8 written
   Partner reviewed + approved
   Saved in Google Docs
```

---

### STEP 10 — Mailmeteor Setup
```
Time: 20 minutes

□ Go to mailmeteor.com
□ Click: Add to Google Sheets
□ Connect to Gmail
□ Allow all permissions

□ Open Google Sheets
□ Extensions → Mailmeteor
□ Confirm it loads

□ Set up first campaign:
   → Subject:
     quick question {{First Name}}
   → Body: paste Email 1
   → Sender: [Partner Name]
   → From: hello@[domain].com

□ Send test to yourself:
   → Preview → Send test
   → Check inbox
   → Tokens replaced correctly?
   → Looks clean?

□ Fix anything off

✅ Done when:
   Mailmeteor connected
   Test email received
   Looks professional
```

---

### STEP 11 — Follow Up System
```
Time: 30 minutes

□ Open LEADS tab
□ Add conditional formatting:
   → Select Follow Up Date column
   → Format → Conditional formatting

   Rule 1:
   → Date is today
   → Color: Yellow

   Rule 2:
   → Date is past
   → Color: Red

Now overdue follow-ups
show red automatically

□ Write partner instructions:
   Open Google Docs
   New doc: "Partner Daily Process"

   Write:
   ---
   Every morning:

   1. Open LEADS sheet
   2. Filter red + yellow rows
   3. These get emailed today
   4. After sending update:
      → Last Contact Date: today
      → Email # Sent: +1
      → Follow Up Date: +3 days
      → Status: Follow Up Sent
   5. Log in METRICS tab
   ---

□ Share doc with partner

✅ Done when:
   Conditional formatting live
   Partner process doc written
   Shared with partner
```

---

## DAY 2 CHECKLIST
```
□ All 8 email templates written
□ Partner reviewed templates
□ Mailmeteor connected + tested
□ Follow-up tracker formatted
□ Partner daily process documented
```

---

# DAY 3 — WEBSITE BUILD
## Tamir builds | Time: 2 hours

---

### STEP 12 — Project Setup
```
Time: 15 minutes

□ Open VS Code
□ Create new folder:
   lean-acquisition-os

□ Create file structure:
   lean-acquisition-os/
   ├── index.html
   ├── css/
   │   └── style.css
   ├── js/
   │   └── main.js
   ├── backend/
   │   ├── app.py
   │   ├── requirements.txt
   │   └── .env
   └── README.md

□ Initialize git:
   git init
   git add .
   git commit -m "initial setup"

□ Create GitHub repo:
   → github.com
   → New repository
   → Name: lean-acquisition-os
   → Private
   → Push local to remote

✅ Done when:
   Folder structure created
   Git initialized
   GitHub repo created
```

---

### STEP 13 — Landing Page
```
Time: 60 minutes

BUILD index.html:

This page does one thing:
Get them to book a call

Sections:
1. Headline
2. What you do
3. How it works
4. Pilot offer
5. Book call button

□ Headline:
   "We Install a Client
    Acquisition System That
    Turns Missed Leads Into
    Booked Revenue — Automatically"

□ Subheadline:
   "Done-for-you lead outreach,
    follow-up automation, and
    booking management for
    service businesses"

□ How it works (3 steps):
   Step 1: We find your ideal clients
   Step 2: We run the full sequence
   Step 3: Qualified calls land
            on your calendar

□ Pilot offer section:
   "Taking 3 Pilot Clients
    This Month"

   $1,000/month
   → Full system installed
   → Done-for-you outreach
   → Weekly performance reports
   → In exchange for case study

□ Single CTA button:
   "Book Your Free 15-Min Call"
   → Links to Calendly

□ Style it clean:
   → Dark background
   → White text
   → One accent color
   → Mobile responsive
   → Fast loading

✅ Done when:
   Page looks professional
   CTA links to Calendly
   Mobile responsive
```

---

### STEP 14 — Python Flask Backend
```
Time: 45 minutes

This handles:
→ Contact form submissions
→ MailerLite API calls
→ Any future automation

□ Install Flask:
   pip install flask
   pip install requests
   pip install python-dotenv
   pip install flask-cors

□ requirements.txt:
   flask
   requests
   python-dotenv
   flask-cors

□ .env file:
   MAILERLITE_API_KEY=your_key
   CLAUDE_API_KEY=your_key
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id

□ app.py basic structure:

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import os

load_dotenv()
app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "running"})

@app.route('/contact', methods=['POST'])
def contact():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    # Add to MailerLite
    # Send Telegram alert
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)

□ Test it runs:
   python app.py
   → Should see:
     Running on http://127.0.0.1:5000

✅ Done when:
   Flask runs locally
   Health endpoint returns response
```

---

## DAY 3 CHECKLIST
```
□ VS Code project created
□ GitHub repo created
□ Landing page built
□ Flask backend running
□ File structure clean
```

---

# DAY 4 — INTEGRATIONS
## Tamir builds | Time: 2 hours

---

### STEP 15 — MailerLite Integration
```
Time: 30 minutes

□ Go to mailerlite.com
□ Create account free
□ Verify domain email

□ Create group:
   → Subscribers → Groups
   → New group
   → Name: LAO Leads

□ Get API key:
   → Integrations → API
   → Copy API key
   → Add to .env file

□ Update app.py contact route:

@app.route('/contact', methods=['POST'])
def contact():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    
    # Add to MailerLite
    headers = {
        'Authorization': 
        f'Bearer {os.getenv("MAILERLITE_API_KEY")}',
        'Content-Type': 'application/json'
    }
    payload = {
        'email': email,
        'fields': {'name': name},
        'groups': ['YOUR_GROUP_ID']
    }
    requests.post(
        'https://connect.mailerlite.com'
        '/api/subscribers',
        json=payload,
        headers=headers
    )
    
    return jsonify({"success": True})

□ Test with real email:
   → Submit form
   → Check MailerLite
   → Subscriber appears? ✅

✅ Done when:
   Form submit → MailerLite ✅
```

---

### STEP 16 — Telegram Alert Integration
```
Time: 30 minutes

□ Add to app.py:

def send_telegram(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    requests.post(url, json={
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    })

□ Call it in contact route:

send_telegram(
    f"🔥 NEW LEAD\n\n"
    f"Name: {name}\n"
    f"Email: {email}\n\n"
    f"Added to MailerLite ✅"
)

□ Test it:
   → Submit form
   → Telegram fires? ✅
   → Both you and partner 
     get the alert?

□ Add partner Chat ID:
   → Send alert to both:

def send_telegram(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_ids = [
        os.getenv('TELEGRAM_CHAT_ID'),
        os.getenv('PARTNER_CHAT_ID')
    ]
    for chat_id in chat_ids:
        url = (f'https://api.telegram.org'
               f'/bot{token}/sendMessage')
        requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        })

□ Add PARTNER_CHAT_ID to .env

✅ Done when:
   Both get Telegram alerts
   On every form submit
```

---

### STEP 17 — Stripe Integration
```
Time: 45 minutes

□ Go to stripe.com
□ Create account
□ Complete verification

□ Create product:
   → Products → Add product
   → Name: LAO Pilot Client
   → Price: $1,000/month recurring
   → Save

□ Copy payment link:
   → Payment links → Create
   → Select LAO Pilot Client
   → Copy link
   → Add to landing page
     as secondary CTA:
     "Ready to Start? 
      Pay Pilot Fee →"

□ Install stripe in Python:
   pip install stripe
   Add to requirements.txt

□ Add webhook endpoint
   for payment confirmation:

@app.route('/stripe-webhook', 
           methods=['POST'])
def stripe_webhook():
    payload = request.data
    # Verify payment
    # Send Telegram alert
    send_telegram(
        "💰 PAYMENT RECEIVED\n\n"
        "New pilot client signed ✅\n"
        "Check email for details"
    )
    return jsonify({"success": True})

✅ Done when:
   Stripe account live
   Payment link created
   Added to landing page
   Webhook endpoint built
```

---

## DAY 4 CHECKLIST
```
□ MailerLite connected
□ Form submissions captured
□ Telegram alerts firing
□ Both partners get alerts
□ Stripe account live
□ Payment link on landing page
```

---

# DAY 5 — MAKE.COM AUTOMATIONS
## Tamir builds | Time: 2-3 hours

---

### STEP 18 — Lead Scorer Automation
```
Time: 60 minutes

Fires when partner adds
a new lead to Sheets
Scores it with Claude
Alerts both on Telegram

□ Open make.com
□ New scenario
□ Name: LAO Lead Scorer

□ Module 1 — TRIGGER:
   → Google Sheets
   → Watch New Rows
   → Connect Google account
   → Spreadsheet: LAO Master Tracker
   → Sheet: LEADS
   → From Row: 2
   → Limit: 1

□ Module 2 — CLAUDE SCORE:
   → HTTP → Make a request
   → URL:
     https://api.anthropic.com
     /v1/messages
   → Method: POST
   → Headers:
     x-api-key: YOUR_CLAUDE_KEY
     anthropic-version: 2023-06-01
     content-type: application/json
   → Body (Raw JSON):
   {
     "model": 
     "claude-3-haiku-20240307",
     "max_tokens": 200,
     "messages": [{
       "role": "user",
       "content": "Score this lead
       1-10 for a done-for-you
       client acquisition service.
       Name: {{1.First Name}}.
       Company: {{1.Company}}.
       Niche: {{1.Niche}}.
       Return JSON only:
       {score: number,
       reason: one sentence,
       priority: high/medium/low}"
     }]
   }

□ Module 3 — FILTER:
   → Add filter after Module 2
   → Only continue if score > 6

□ Module 4 — TELEGRAM:
   → Telegram Bot
   → Send a Message
   → Add bot token
   → Chat ID: Tamir
   → Message:
   "🎯 QUALIFIED LEAD

   Name: {{1.First Name}} 
          {{1.Last Name}}
   Company: {{1.Company}}
   Email: {{1.Email}}
   Niche: {{1.Niche}}
   Source: {{1.Source}}

   Score: [from Claude]
   Reason: [from Claude]
   Priority: [from Claude]

   → Outreach today?"

□ Add second Telegram module:
   → Same message
   → Partner Chat ID

□ Turn ON
□ Test with new row in Sheets
□ Alert fires? ✅

✅ Done when:
   New lead → scored → 
   alert fires for both
```

---

### STEP 19 — Reply Classifier
```
Time: 60 minutes

Fires when partner marks
a lead as Replied in Sheets
Classifies with Claude
Suggests reply for partner

□ New scenario in Make.com
□ Name: LAO Reply Classifier

□ Module 1 — TRIGGER:
   → Google Sheets Watch Rows
   → Same sheet
   → Add filter:
     Status column = Replied

□ Module 2 — CLAUDE CLASSIFY:
   → HTTP request (same setup)
   → Body:
   {
     "model":
     "claude-3-haiku-20240307",
     "max_tokens": 300,
     "messages": [{
       "role": "user",
       "content": "Classify this
       email reply from a
       business owner.

       Reply: {{1.Notes}}

       Categories:
       INTERESTED
       NOT NOW
       NOT INTERESTED
       QUESTION

       Return JSON only:
       {
         category: string,
         suggested_reply:
         2-3 sentence natural reply
         that moves toward booking,
         urgency: high/medium/low
       }"
     }]
   }

□ Module 3 — TELEGRAM:
   → Send to both partners:
   "📩 REPLY RECEIVED

   Name: {{1.First Name}}
   Company: {{1.Company}}

   Status: [category]
   Urgency: [urgency]

   Their message:
   {{1.Notes}}

   Suggested reply:
   [suggested_reply]

   Reply within 2 hours ⚡"

□ Turn ON
□ Test by adding Replied row
□ Alert fires with 
  classification? ✅

✅ Done when:
   Status Replied →
   both get classified alert
```

---

## DAY 5 CHECKLIST
```
□ Lead scorer built + tested
□ Reply classifier built + tested
□ Both scenarios turned ON
□ Both partners getting alerts
□ Everything connected
```

---

# DAY 6 — DEPLOY + HANDOFF
## Tamir builds | Time: 2 hours

---

### STEP 20 — Deploy Frontend
```
Time: 30 minutes

□ Go to vercel.com
□ Sign up free
□ Connect GitHub account

□ Import repository:
   → New Project
   → Select: lean-acquisition-os
   → Framework: Other
   → Root directory: ./
   → Deploy

□ After deploy:
   → Copy live URL
   → Test all links work
   → Test on mobile
   → CTA button works?
   → Calendly opens? ✅

□ Add custom domain
   if partner has one:
   → Settings → Domains
   → Add domain
   → Update DNS records

✅ Done when:
   Site is live on real URL
   Mobile looks clean
   All buttons work
```

---

### STEP 21 — Deploy Backend
```
Time: 30 minutes

□ Go to railway.app
□ Sign up free
□ Connect GitHub

□ New project:
   → Deploy from GitHub repo
   → Select backend folder
   → Add environment variables
     (copy from .env file)

□ After deploy:
   → Copy Railway URL
   → Update frontend JS
     to point to Railway URL
     instead of localhost

□ Test live:
   → Submit contact form
     on live Vercel site
   → MailerLite gets subscriber?
   → Telegram fires? ✅

✅ Done when:
   Backend live on Railway
   Frontend connected to it
   Full flow tested end to end
```

---

### STEP 22 — Partner Handoff
```
Time: 30 minutes

□ Create handoff document:
   Google Doc: 
   "LAO Partner Operations Guide"

   Include:
   → Live website URL
   → Calendly link
   → HubSpot login
   → Apollo login
   → Google Sheets link
   → Gmail login
   → Mailmeteor instructions
   → Daily process (Step 11)
   → Email sequence guide
   → 4-step close script
   → Telegram bot is live
     (alerts will fire automatically)

□ Walk partner through:
   → 15 minute call or Loom video
   → Show him every tool
   → Show him daily process
   → Show him how Telegram
     alerts work
   → Show him HubSpot pipeline

□ Partner starts Day 8:
   → Find 40 leads
   → Send first 20 emails
   → Log everything in Sheets
   → Tamir monitors alerts

✅ Done when:
   Partner has everything
   Understands daily process
   Ready to start Day 8
```

---

## DAY 6 CHECKLIST
```
□ Frontend live on Vercel
□ Backend live on Railway
□ Full flow tested live
□ Partner handoff doc written
□ Partner walkthrough done
□ Partner ready for Day 8
```

---

# DAY 7 — TEST + OPTIMIZE
## Tamir + Partner | Time: 2 hours

---

### STEP 23 — Full System Test
```
Time: 60 minutes

Test every single flow:

□ New lead added to Sheets
   → Telegram fires for both ✅

□ Lead marked as Replied
   → Classification alert fires ✅

□ Contact form submitted
   on live website
   → MailerLite captures it ✅
   → Telegram fires for both ✅

□ Calendly link clicked
   → Booking page loads ✅
   → Test booking goes through ✅
   → Calendar invite sent ✅

□ Stripe payment link
   → Opens correctly ✅
   → Test mode payment works ✅
   → Webhook fires ✅
   → Telegram alert fires ✅

□ HubSpot pipeline
   → Move test lead through
     all 7 stages ✅
   → Partner can do this? ✅

□ Email from Gmail
   → Lands in inbox not spam ✅
   → Signature shows correctly ✅
   → Mailmeteor sends test ✅

Fix anything that fails
before partner starts
```

---

### STEP 24 — Benchmarks Set
```
Time: 30 minutes

□ Open METRICS tab
□ Set Week 1 targets:

   Reply rate target: 3-8%
   Booking rate target: 15-30%
   Show rate target: 60-80%
   Close rate target: 20-40%

□ Create Friday review reminder:
   → Google Calendar
   → Every Friday 4pm
   → Title: LAO Weekly Review
   → Recurring: weekly

□ Review process every Friday:
   Below 3% reply rate:
   → Tamir checks email setup
   → Partner rewrites subject lines
   → Test 3 new versions

   Below 15% booking rate:
   → Simplify CTA
   → Cut email word count
   → Reduce Calendly friction

   Below 60% show rate:
   → Add reminder emails
   → Tamir builds reminder 
     automation in Make.com

□ Document baseline:
   Week 1 starts at zero
   Week 2 = first real data
   Week 3 = first optimization

✅ Done when:
   Benchmarks documented
   Friday review scheduled
   Both partners aligned
```

---

## DAY 7 CHECKLIST
```
□ Every flow tested end to end
□ All bugs fixed
□ Benchmarks set
□ Friday reviews scheduled
□ System is ready
□ Partner starts Day 8 🚀
```

---

# DAY 8+ — PARTNER EXECUTION
## Partner runs daily | Tamir monitors

---

```
PARTNER DAILY ROUTINE:

MORNING (2 hours):
8:00am — Open LEADS sheet
  → Filter red + yellow rows
  → These get emailed first

8:15am — Find 30-40 leads
  → 10 Apollo
  → 10 LinkedIn
  → 10 Google Maps
  → 10 website contacts

9:15am — Send 30-50 emails
  → Follow-ups first
  → New outreach second
  → Log everything

AFTERNOON (2 hours):
1:00pm — Check replies
  → Open Gmail
  → Update status to Replied
  ��� Check Telegram classification
  → Reply within 2 hours

2:00pm — Discovery calls
  → Max 2 per day
  → Follow 4-step close
  → Log outcome in sheet

3:00pm — Admin
  → Update HubSpot stages
  → Set follow-up dates
  → Update METRICS tab

FRIDAY (extra 30 min):
4:00pm — Weekly review
  → Check metrics vs benchmarks
  → Flag anything to Tamir
  → Send client reports
    (once clients signed)

---

TAMIR DAILY CHECK (15 min):
→ Check Telegram alerts
→ Any bugs to fix?
→ Any automation failures?
→ Update partner if needed
→ Back to Client System Pros
```

---

# FIRST CLIENT PROCESS
## Partner leads | Tamir supports

---

### STEP 25 — Pilot Pitch
```
When a warm lead is ready:

Partner sends this DM:

"Hey [Name] —

Taking on 3 pilot clients
this month for our client
acquisition system.

Reduced rate in exchange
for a case study.

Based on what you shared
about [specific thing] —
I think [their business]
would be a strong fit.

Worth 15 minutes to
see if it makes sense?

[Calendly link]"

□ Log in LEADS sheet:
   Status: Pilot Pitch Sent
   Follow Up: today + 3 days
```

---

### STEP 26 — Discovery Call
```
BEFORE CALL — Partner:
□ Review booking form answers
□ Visit their website
□ Check LinkedIn

BEFORE CALL — Tamir:
□ Run Claude pre-brief:
   "Research [company].
    They are a [niche] business.
    Give me:
    3 likely pain points
    1 growth opportunity
    Best sales angle
    in 5 bullet points"
□ Send brief to partner
   before the call

DURING CALL — Partner:
□ Step 1 — Current system:
   "Walk me through exactly
    how you get clients today"

□ Step 2 — Breakdown:
   "Where do leads fall
    through right now?"

□ Step 3 — Cost:
   "What does that cost you
    over 12 months?"

□ Step 4 — Solution:
   "Here is exactly what
    we would install for you"
   → Show the pipeline
   → Show the email sequence
   → Show the automation

□ Close:
   "We have one pilot spot left.
    Want to move forward?"

AFTER CALL:
□ Update HubSpot stage
□ Yes → send contract same day
□ Maybe → send case study
         follow up 48 hours
□ No → log reason
        add to 90-day sequence
```

---

### STEP 27 — Close + Onboard
```
When they say YES:

□ Partner sends contract:
   Google Doc — simple language
   → Scope: lead gen + outreach
     + booking management
   → Price: $1,000/month pilot
   → Payment: monthly via Stripe
   → Start: [date]
   → Duration: month to month
   → Cancel: 30 days notice
   → Client rules:
     Respond to leads in 5 min
     Weekly check-ins required
     CRM use required
   → Guarantee clause

□ Tamir sends Stripe link:
   → $1,000 recurring monthly
   → Do NOT start until paid
   → No exceptions

□ Partner sends onboarding form:
   Google Form: LAO Onboarding
   Questions:
   1. Describe your ideal client
   2. Current monthly revenue
   3. How do you close clients?
   4. Describe your offer
   5. Share your calendar link
   6. What CRM do you use now?

□ Tamir logs in CLIENTS tab:
   → All client details
   → Start date
   → Monthly fee: $1,000
   → Tamir cut: $500
   → Partner cut: $500

□ Kickoff call within 48 hours:
   → Partner runs it
   → 60 minutes
   → Set 30-day targets
   → Define qualified call
   → Set expectations

✅ FIRST CLIENT SIGNED 🔥
```

---

# WEEKLY CLIENT REPORT
## Partner sends every Friday

---

```
Template:

"📊 Weekly Report — [Name]
Week of [date]

📈 THIS WEEK:
→ Leads found: [X]
→ Emails sent: [X]
→ Reply rate: [X]%
→ Calls booked: [X]
→ Show rate: [X]%

🏆 TOP WIN:
[Best result this week]

📋 NEXT WEEK:
[One improvement being made]

System: ✅ Running"

Send every Friday
No exceptions
Clients who see data stay
Clients who feel ignored leave
```

---

# UPGRADE TRIGGERS

---

```
AT 3 CLIENTS ($3,000/month):
□ Upgrade Make.com → $9/month
□ Upgrade Apollo → $49/month
□ Hire VA for lead finding
   ($400-600/month)
□ VA cost split 50/50

AT 5 CLIENTS ($5,000/month):
□ Add GoHighLevel → $97/month
□ Move all clients to GHL
□ GHL affiliate starts paying
   Tamir through 
   Client System Pros ✅

AT 7 CLIENTS ($7,000/month):
□ Add client success person
□ They handle weekly check-ins
□ Partner handles architecture

AT 10 CLIENTS ($10,000/month):
□ $5,000/month each
□ System runs itself
□ Weekly optimization only
□ Both trading fully funded
```

---

# REVENUE TRACKER
## Log every Friday

---

```
Open REVENUE tab in Sheets

Every month log:

Gross Revenue:
→ All client fees combined

Tool Costs:
→ Claude API
→ Make.com
→ Apollo
→ Any other tools

Net Revenue:
→ Gross minus tool costs

Tamir 50%:
→ Net × 0.5

Partner 50%:
→ Net × 0.5

Transfer on 1st of each month
No exceptions
```

---

# FINAL CHECKLIST

---

```
DAY 1:
□ Partnership doc signed
□ Gmail created
□ HubSpot built
□ Apollo set up
□ Calendly live
□ Telegram bot created
□ Claude API loaded
□ Make.com account ready
□ Google Sheets built
□ Partner has all access

DAY 2:
□ 8 email templates written
□ Partner reviewed templates
□ Mailmeteor connected
□ Follow-up tracker formatted
□ Partner process documented

DAY 3:
□ VS Code project created
□ GitHub repo created
□ Landing page built
□ Flask backend running

DAY 4:
□ MailerLite connected
□ Telegram alerts firing
□ Stripe live + payment link up

DAY 5:
□ Lead scorer built + tested
□ Reply classifier built + tested
□ Both automations live

DAY 6:
□ Frontend live on Vercel
□ Backend live on Railway
□ Partner handoff complete

DAY 7:
□ All flows tested end to end
□ Benchmarks set
□ Friday reviews scheduled
□ System ready for partner

DAY 8:
□ Partner starts outreach
□ Tamir monitors + maintains
□ Machine is live 🚀

WEEK 3:
□ First discovery call done
□ First pilot pitched

WEEK 4:
□ First client signed ✅
□ First payment received ✅
□ $500 to Tamir ✅
□ $500 to Partner ✅
□ Machine is real 🔥
```

---

## THE TRUTH

```
Tamir built the machine
Partner runs the machine
Revenue splits 50/50

Your job after Day 7:
→ Monitor Telegram alerts
→ Fix bugs when they appear
→ Add features as needed
→ 15 minutes per day max

Everything else is
the partner executing

You built it once
It works forever

Stack this on top of
Client System Pros
running in the mornings

Two income streams
One skill set
One platform
Maximum leverage 🔥
```
