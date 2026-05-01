# AUTONOMOUS REVENUE ENGINE — CLIENT ACQUISITION SYSTEM
### Partnership: Tamir Robertson + Donald L. Louis Jr.
### Tamir Role: Tech Builder
### Donald Role: Strategy + Outreach + Sales
### Split: 50/50
### Start: May 2026

---

## CORE PRINCIPLE

```
This is not automation.
This is a system that
observes, decides, acts,
and improves daily.
```

---

## OBJECTIVE

```
Build a lean, agent driven system
that consistently generates
qualified leads, converts them
into booked calls, and closes them
into paying clients with minimal
manual effort.

Predictable. Scalable.
Self improving.
```

---

## TARGET LANE

```
Primary ICP:
Local service based businesses

Revenue range:
$10,000 to $50,000 monthly

Core problem:
Leads are being generated
but not converted due to:
→ Slow response
→ Lack of follow up
→ No structured system
```

---

## THE OFFER

```
"We help local service businesses
recover 20 to 40 percent of
missed leads in 14 days by
installing automated follow up
systems that convert existing
traffic into booked jobs."
```

---

## MONETIZATION STRUCTURE

```
Step 1 — Free Audit
→ Identify missed revenue
→ No cost to client
→ Opens the door

Step 2 — Quick Win
→ Fast system implementation
→ Prove it works in 14 days

Step 3 — Retainer
→ Full automation
→ Ongoing optimization
→ $1,500 to $3,000/month

Optional:
→ Performance based upside
→ % of recovered revenue
```

---

## SYSTEM MATH

```
Daily:    50 outreach messages
Monthly:  1,500 messages sent

10% reply rate  = 150 replies
40% booking rate = 60 calls
30% close rate  = 18 clients

Average client: $1,500-$3,000/month
Monthly potential: $27,000-$54,000
```

---

## SYSTEM ARCHITECTURE — 5 AGENTS

---

### AGENT 1 — LEAD INTELLIGENCE ENGINE

```
Purpose:
Continuously source
qualified leads

How it works:
→ Apollo.io pulls leads daily
→ Filters by ICP criteria:
   Local service business
   $10k-$50k revenue
   1-50 employees
→ Claude scores each lead 1-10
→ Only 7+ scores enter pipeline
→ Auto adds to Google Sheets
→ Telegram alert fires to both

AI Stack:
→ Apollo.io (sourcing)
→ Claude API (scoring)
→ Make.com (automation)
→ Google Sheets (storage)
```

---

### AGENT 2 — CONTEXT AND PERSONALIZATION ENGINE

```
Purpose:
Identify real problems and
create relevant outreach angles

How it works:
→ Claude reads lead data
→ Researches their business
→ Identifies likely pain point
→ Writes custom first line
   for every single email
→ Personalizes at scale

AI Stack:
→ Claude API (research + writing)
→ Make.com (trigger)
→ Google Sheets (input/output)

Example output:
"Saw you're running Google Ads
for your HVAC business —
most companies lose 30% of
those leads to slow follow up..."
```

---

### AGENT 3 — OUTREACH ENGINE

```
Purpose:
Start conversations at scale

How it works:
→ Personalized email sequence
→ 8 touch points over 90 days
→ Claude written first lines
→ Sent via Mailmeteor
→ Max 30-50 emails per day
→ Domain warmed before scaling
→ No spam language ever

Sequence:
Email 1 — Day 1   — Curiosity hook
Email 2 — Day 3   — Value add
Email 3 — Day 7   — Direct ask
Email 4 — Day 14  — Soft follow up
Email 5 — Day 30  — Reactivation
Email 6 — Day 45  — Check in
Email 7 — Day 60  — Check in
Email 8 — Day 90  — Final attempt

Guardrails:
→ Max 50 emails/day
→ Lead score 7+ only
→ Domain warm up required
→ No spam trigger words
→ SPF + DKIM + DMARC active
```

---

### AGENT 4 — FOLLOW UP INTELLIGENCE ENGINE

```
Purpose:
Maximize response and
recover missed opportunities

How it works:
→ Lead replies to email
→ Claude reads the reply
→ Classifies it instantly:
   INTERESTED — route to booking
   NOT NOW    — schedule follow up
   UNSUBSCRIBE — remove immediately
   QUESTION   — draft response
   MEETING READY — book call now
→ Telegram alert fires to Donald
→ HubSpot stage updates auto
→ Calendly link sent if interested

AI Stack:
→ Claude API (classifier)
→ Make.com (trigger + routing)
→ HubSpot (pipeline update)
→ Telegram (alert to Donald)
→ Calendly (auto booking)
```

---

### AGENT 5 — OPTIMIZATION ENGINE

```
Purpose:
Continuously improve performance

How it works:
→ Weekly performance pull
   from Google Sheets
→ Claude analyzes:
   Reply rates by subject line
   Reply rates by day/time
   Best performing email copy
   Lead score vs close rate
→ Generates weekly report
→ Sends to both via Telegram
→ Recommendations included

Tracks:
→ Emails sent vs replies
→ Reply rate trends
→ Call show rates
→ Close rates
→ Revenue per lead

AI Stack:
→ Claude API (analysis)
→ Google Sheets (data)
→ Make.com (weekly trigger)
→ Telegram (report delivery)
```

---

## CONVERSION SYSTEM

```
Lead responds to email
         ↓
Auto qualification questions sent
         ↓
Claude scores response
         ↓
Qualified → Calendly link sent
         ↓
Call booked automatically
         ↓
Donald gets Telegram alert
         ↓
Discovery call runs
```

---

## CALL STRUCTURE

```
1. Diagnose current lead flow
2. Identify missed revenue gaps
3. Present simple system solution
4. Close with clear next step

Target: 15 minutes
Goal: Audit or paid engagement
```

---

## DELIVERY SYSTEM (CLIENT ONBOARDING)

```
Day 1-2:  Client onboarding + audit
Day 3-5:  System installation
Week 2:   Optimization + tracking
Ongoing:  Monthly performance reports
```

---

## BEFORE YOU START

```
Donald handles:
→ Lead finding
→ Email outreach
→ Sales calls
→ Client management
→ Strategy decisions

Tamir handles:
→ Every technical build
→ All 5 agents
→ Automations
→ Website
→ Integrations
→ Systems

Time per day: 2 hours max
   (afternoons only)
   (mornings = Client System Pros)

Total build time: 7 days
Donald starts outreach: Day 8
First client target: Day 21
```

---

## PARTNERSHIP AGREEMENT

```
Tamir Robertson + Donald L. Louis Jr.
Date: May 2026

Role — Tamir:
→ All technical builds
→ Automations + integrations
→ Website + systems
→ Maintenance + bug fixes

Role — Donald:
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
```

---

# DAY 1 — CORE INFRASTRUCTURE
## Tamir builds | Time: 2 hours

---

### STEP 1 — Gmail Account
```
Time: 15 minutes

✅ Email created:
   tamir@clientmachinery.com
   donald@clientmachinery.com

✅ Professional signature set

✅ SPF + DKIM + DMARC active

✅ Warmup emails sent

✅ Login shared with Donald

COMPLETE
```

---

### STEP 2 — HubSpot CRM
```
Time: 20 minutes

□ Go to hubspot.com
□ Sign up with Gmail

□ Rename pipeline to:
   LAO Acquisition

□ Set 7 stages:
  1. Lead Found
  2. Outreach Sent
  3. Replied
  4. Call Booked
  5. Call Completed
  6. Proposal Sent
  7. Client Signed

□ Turn off all notifications

□ Invite Donald:
   donald@clientmachinery.com

✅ Done when:
   Pipeline built
   Donald has access
```

---

### STEP 3 — Apollo.io
```
Time: 15 minutes

□ Go to apollo.io
□ Sign up free
□ Complete profile:
   Name: Donald L. Louis Jr.
   Company: Client Acquisition System
   Website: clientmachinery.com

□ Test first search:
   Job title: Agency Owner
   OR Home Services Owner
   OR Local Service Business
   Location: United States
   Company size: 1-50
   Revenue: $10k-$50k/month
   Save as: "Local Service ICP"

□ Share login with Donald

✅ Done when:
   Account created
   First search saved
   Donald has login
```

---

### STEP 4 — Calendly
```
Time: 15 minutes

□ Go to calendly.com
□ Sign up free
□ Connect Gmail calendar

□ Create event:
   Name: Free Lead Recovery Audit
   Duration: 15 minutes
   Location: Google Meet
   Buffer: 15 min after

□ Set availability:
   Monday-Thursday only
   10am-4pm Donald timezone
   Max 2 calls per day

□ Add 3 intake questions:

   Question 1:
   "What is your current
    monthly revenue?"
   (required)

   Question 2:
   "How are you currently
    getting new leads?"
   (required)

   Question 3:
   "What happens when a
    lead does not respond
    to your first contact?"
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
□ Name: CAS Alerts
□ Username: CASAlertsBot

□ Save:
   Bot API token
   Your Chat ID
   Donald Chat ID

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
□ Create API key: CAS Main
□ Add $10 credit
□ Test API call

✅ Done when:
   Key saved
   $10 loaded
   Test response received
```

---

### STEP 7 — Make.com
```
Time: 10 minutes

□ Go to make.com
□ Sign up free
□ Account only — build Day 5

✅ Done when:
   Account created
```

---

### STEP 8 — Google Sheets Tracker
```
Time: 30 minutes

□ Name: CAS Master Tracker

□ TAB 1 — LEADS:
   A: First Name
   B: Last Name
   C: Company
   D: Email
   E: LinkedIn URL
   F: Website
   G: Niche
   H: Source
   I: Status
   J: AI Score (1-10)
   K: Pain Point (Claude)
   L: Custom First Line (Claude)
   M: Last Contact Date
   N: Follow Up Date
   O: Email # Sent
   P: Reply Classification
   Q: Notes

□ TAB 2 — METRICS:
   A: Date
   B: Leads Found
   C: Leads Scored 7+
   D: Emails Sent
   E: Replies Received
   F: Reply Rate %
   G: Calls Booked
   H: Calls Completed
   I: Show Rate %
   J: Closed
   K: Close Rate %
   L: Revenue
   M: Notes

□ TAB 3 — CLIENTS:
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
   A: Month
   B: Gross Revenue
   C: Tool Costs
   D: Net Revenue
   E: Tamir 50%
   F: Donald 50%
   G: Notes

□ Share with Donald

✅ Done when:
   All 4 tabs built
   Donald has access
```

---

## DAY 1 CHECKLIST
```
✅ Gmail created + warmed
□ HubSpot pipeline built
□ Apollo set up
□ Calendly link live
□ Telegram bot created
□ Claude API loaded + tested
□ Make.com account ready
□ Google Sheets tracker built
□ Donald has access to all tools
```

---

# DAY 2 — EMAIL + OUTREACH SYSTEM
## Tamir builds | Time: 2 hours

---

### STEP 9 — Email Templates
```
Time: 45 minutes

□ Open Google Docs
□ Name: CAS Email Templates

□ Write 8 emails
   Focus on:
   → Missed lead recovery angle
   → Under 100 words each
   → One idea per email
   → Clear CTA every time

   Hook to use:
   "Most [niche] businesses lose
    20-40% of leads to slow
    follow up — we fix that
    in 14 days"

   Tokens:
   {{First Name}}
   {{Company}}
   {{Niche}}
   {{Custom Line}} ← Claude writes this

   Email 1 — Day 1  — Curiosity
   Email 2 — Day 3  — Value
   Email 3 — Day 7  — Direct Ask
   Email 4 — Day 14 — Soft
   Email 5 — Day 30 — Reactivation
   Email 6 — Day 45 — Check In
   Email 7 — Day 60 — Check In
   Email 8 — Day 90 — Final

□ Donald reviews + approves

✅ Done when:
   All 8 written
   Donald approved
   Saved in Google Docs
```

---

### STEP 10 — Mailmeteor Setup
```
Time: 20 minutes

□ Add to Google Sheets
□ Connect to Gmail
□ Test campaign setup
□ Send test to yourself

✅ Done when:
   Connected
   Test email clean
```

---

### STEP 11 — Follow Up System
```
Time: 30 minutes

□ Conditional formatting on
   Follow Up Date column:
   Red = overdue
   Yellow = today

□ Write Donald daily process doc

✅ Done when:
   Formatting live
   Process doc shared
```

---

# DAY 3 — WEBSITE BUILD
## Tamir builds | Time: 2 hours

---

### STEP 12 — Project Setup
```
□ VS Code folder:
   client-acquisition-system

□ File structure:
   ├── index.html
   ├── css/style.css
   ├── js/main.js
   ├── backend/
   │   ├── app.py
   │   ├── requirements.txt
   │   └── .env
   └── README.md

□ Git init + GitHub push

✅ Done when:
   Structure created
   GitHub repo live
```

---

### STEP 13 — Landing Page
```
Time: 60 minutes

Headline:
"We Help Local Service Businesses
 Recover 20-40% of Missed Leads
 in 14 Days — Guaranteed"

Subheadline:
"Done-for-you automated follow up
 systems that convert your existing
 traffic into booked jobs"

How it works:
Step 1: Free audit of your lead flow
Step 2: We install the system in 48hrs
Step 3: Missed leads start converting

Pilot offer:
"Taking 3 Clients This Month"
$1,500/month
→ Full system installed
→ Automated follow up active
→ Weekly performance reports
→ In exchange for case study

CTA:
"Book Your Free Lead Recovery Audit"
→ Links to Calendly

✅ Done when:
   Page live
   CTA working
   Mobile responsive
```

---

### STEP 14 — Python Flask Backend
```
Time: 45 minutes

Handles:
→ Form submissions
→ MailerLite API
→ Telegram alerts
→ Claude API calls

□ Install:
   flask
   requests
   python-dotenv
   flask-cors
   anthropic

□ .env file:
   MAILERLITE_API_KEY=
   CLAUDE_API_KEY=
   TELEGRAM_BOT_TOKEN=
   TELEGRAM_CHAT_ID=
   PARTNER_CHAT_ID=

✅ Done when:
   Flask runs locally
   Health endpoint works
```

---

# DAY 4 — INTEGRATIONS
## Tamir builds | Time: 2 hours

---

### STEP 15 — MailerLite
```
□ Create account
□ Create group: CAS Leads
□ Get API key
□ Connect to Flask backend
□ Test form submission

✅ Done when:
   Form → MailerLite works
```

---

### STEP 16 — Telegram Alerts
```
□ Alert fires on:
   → New lead added
   → Reply received
   → Call booked
   → Payment received

□ Both Tamir + Donald get alerts

✅ Done when:
   Both get alerts
```

---

### STEP 17 — Stripe
```
□ Create account
□ Product: CAS Pilot Client
□ Price: $1,500/month recurring
□ Payment link on landing page
□ Webhook → Telegram alert

✅ Done when:
   Payment link live
   Webhook firing
```

---

# DAY 5 — 5 AGENT BUILD
## Tamir builds | Time: 3 hours

---

### STEP 18 — Agent 1: Lead Intelligence
```
Make.com scenario:

Trigger: Google Sheets new row
→ Pull lead data
→ Send to Claude:
   Score this lead 1-10
   Based on ICP criteria
→ Write score to Sheet
→ If score 7+:
   Move to outreach queue
   Fire Telegram alert

Claude prompt:
"Score this lead 1-10
 based on fit for local
 service business ICP.
 Return score + reason only."
```

---

### STEP 19 — Agent 2: Personalization
```
Make.com scenario:

Trigger: Lead score 7+ added
→ Send to Claude:
   Research pain point
   Write custom first line
→ Write back to Sheet:
   Column K: Pain Point
   Column L: Custom First Line

Claude prompt:
"You are writing the first line
 of a cold email to {{Company}}.
 They are a {{Niche}} business.
 Write one sentence that shows
 you understand their specific
 lead conversion problem.
 Under 20 words. No fluff."
```

---

### STEP 20 — Agent 3: Outreach Engine
```
Mailmeteor sends emails
Using Claude written first lines
From Sheets columns

Daily limit: 50 emails max
Schedule: 9am-11am only
Domain warmed: required first
```

---

### STEP 21 — Agent 4: Reply Classifier
```
Make.com scenario:

Trigger: New email reply detected
→ Send reply text to Claude
→ Claude classifies:
   INTERESTED
   NOT NOW
   QUESTION
   UNSUBSCRIBE
   MEETING READY
→ Write to Sheet column P
→ Fire Telegram to Donald:
   "Reply from {{Name}}
    Classification: INTERESTED
    Reply: [text]
    Book them: [Calendly link]"
→ Update HubSpot stage

Claude prompt:
"Classify this email reply into
 one of these categories:
 INTERESTED / NOT NOW /
 QUESTION / UNSUBSCRIBE /
 MEETING READY.
 Return category only."
```

---

### STEP 22 — Agent 5: Optimization Engine
```
Make.com scenario:

Trigger: Every Monday 8am
→ Pull last 7 days from Sheets
→ Send to Claude:
   Analyze performance
   What is working
   What to improve
→ Claude generates report
→ Send to both via Telegram

Tracks:
→ Reply rates
→ Best subject lines
→ Best sending times
→ Close rate trends
```

---

# DAY 6 — DEPLOYMENT
## Tamir builds | Time: 2 hours

---

### STEP 23 — Deploy to Railway
```
□ Go to railway.app
□ Connect GitHub repo
□ Add environment variables
□ Deploy Flask backend
□ Get live URL
□ Update landing page
   with live backend URL

✅ Done when:
   Backend live on internet
   Form submissions working
```

---

### STEP 24 — Domain Connection
```
□ Point clientmachinery.com
   to Railway deployment
□ SSL active
□ Test all forms
□ Test all alerts

✅ Done when:
   clientmachinery.com live
   All systems connected
```

---

# DAY 7 — TEST + LAUNCH
## Tamir builds | Time: 2 hours

---

### STEP 25 — Full System Test
```
□ Add test lead to Sheets
□ Agent 1 scores it
□ Agent 2 personalizes it
□ Email sends via Mailmeteor
□ Reply test → classified
□ Telegram alerts fire
□ HubSpot updates
□ Weekly report generates

All 5 agents firing? ✅
```

---

### STEP 26 — Donald Launch Prep
```
□ Share all logins
□ Walk through daily process
□ Show Telegram alerts
□ Show HubSpot pipeline
□ Donald ready for Day 8

Donald starts outreach: Day 8
First client target: Day 21
```

---

## DAY 7 CHECKLIST
```
□ All 5 agents live
□ Full test completed
□ Website live
□ All alerts firing
□ Donald has everything
□ System ready to scale
```

---

## END STATE

```
A system that:
→ Finds leads daily (Agent 1)
→ Personalizes at scale (Agent 2)
→ Outreaches automatically (Agent 3)
→ Classifies + routes replies (Agent 4)
→ Improves itself weekly (Agent 5)

Result:
→ Predictable pipeline
→ Daily opportunities
→ Scalable to $50k/month
→ Minimal manual effort
```

---

*Client Acquisition System — Tamir Robertson + Donald L. Louis Jr. — May 2026*
