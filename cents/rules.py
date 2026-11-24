"""Built-in categorization rules.

Categories are matched against the *normalized* merchant name. Rules are an
ordered list of (category, [substring-patterns]); the first category whose
pattern matches wins, so specific categories (Subscriptions, Transport,
Dining) are checked before broad ones (Shopping).
"""

from __future__ import annotations

CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Subscriptions",
    "Shopping",
    "Housing",
    "Utilities",
    "Health",
    "Entertainment",
    "Travel",
    "Personal Care",
    "Education",
    "Income",
    "Transfer",
    "Other",
]

RULES: list[tuple[str, list[str]]] = [
    (
        "Subscriptions",
        [
            r"netflix", r"spotify", r"hulu", r"disney\+", r"disney plus", r"hbo", r"max",
            r"apple", r"icloud", r"apple music", r"prime video", r"youtube premium",
            r"youtube tv", r"audible", r"kindle", r"adobe", r"microsoft", r"office 365",
            r"dropbox", r"notion", r"github", r"chatgpt", r"openai", r"midjourney",
            r"new york times", r"washington post", r"patreon", r"substack",
            r"gym", r"equinox", r"planet fitness", r"la fitness", r"crunch", r"peloton",
            r"headspace", r"calm", r"duolingo", r"linkedin", r"1password", r"lastpass",
            r"nordvpn", r"expressvpn", r"vercel", r"heroku", r"digitalocean", r"linode",
            r"aws", r"twilio", r"cloud", r"hello fresh", r"blue apron",
        ],
    ),
    (
        "Transport",
        [
            r"uber", r"lyft", r"shell", r"chevron", r"exxon", r"\bgas\b", r"fuel", r"parking",
            r"metro", r"transit", r"toll", r"ezpass", r"amtrak", r"taxi", r"chargepoint",
            r"evgo", r"supercharger", r"hertz", r"avis", r"enterprise", r"car rental",
        ],
    ),
    (
        "Dining",
        [
            r"restaurant", r"cafe", r"coffee", r"starbucks", r"mcdonald", r"chipotle",
            r"taco", r"subway", r"domino", r"pizza", r"diner", r"grill", r"bistro",
            r"doordash", r"grubhub", r"ubereats", r"postmates", r"panera", r"sweetgreen",
            r"sushi", r"ramen", r"noodle", r"burger", r"chick fil", r"kfc", r"wendy",
            r"shake shack", r"five guys", r"cheesecake", r"olive garden", r"panda express",
            r"dunkin", r"applebee", r"burger king", r"wingstop", r"cava", r"salad",
        ],
    ),
    (
        "Groceries",
        [
            r"whole foods", r"trader joe", r"safeway", r"kroger", r"aldi", r"publix",
            r"grocery", r"market", r"lidl", r"wegmans", r"sprouts", r"supermarket",
            r"costco", r"grocery outlet",
        ],
    ),
    (
        "Shopping",
        [
            r"amazon", r"walmart", r"target", r"best buy", r"ikea", r"home depot", r"lowes",
            r"ebay", r"etsy", r"zara", r"h&m", r"uniqlo", r"nike", r"adidas", r"apple store",
            r"macy", r"nordstrom", r"sephora", r"ulta", r"wayfair", r"dyson", r"b&h", r"newegg",
            r"temu", r"shein", r"aliexpress",
        ],
    ),
    (
        "Utilities",
        [
            r"electric", r"\bgas\b", r"water", r"pg&e", r"con ed", r"internet", r"xfinity",
            r"comcast", r"spectrum", r"fios", r"sewer", r"trash", r"waste", r"utility",
            r"power", r"energy",
        ],
    ),
    (
        "Health",
        [
            r"cvs", r"walgreens", r"pharmacy", r"rite aid", r"doctor", r"medical",
            r"dental", r"dentist", r"hospital", r"clinic", r"therapy", r"optometry",
            r"glasses", r"copay", r"pharma", r"labcorp", r"quest", r"urgent care",
        ],
    ),
    (
        "Housing",
        [r"rent", r"mortgage", r"landlord", r"housing", r"property", r"hoa", r"maintenance"],
    ),
    (
        "Travel",
        [
            r"airbnb", r"hotel", r"marriott", r"hilton", r"expedia", r"booking", r"kayak",
            r"priceline", r"flight", r"airline", r"delta", r"united", r"southwest",
            r"jetblue", r"airport", r"tsa", r"passport", r"resort",
        ],
    ),
    (
        "Entertainment",
        [
            r"movie", r"amc", r"cinemark", r"regal", r"theater", r"concert",
            r"ticketmaster", r"stubhub", r"bowling", r"arcade", r"twitch", r"redbox",
            r"museum", r"zoo", r"amusement", r"steam", r"nintendo", r"playstation",
            r"xbox", r"game",
        ],
    ),
    (
        "Personal Care",
        [r"salon", r"barber", r"haircut", r"spa", r"nail", r"massage", r"dry clean", r"laundromat"],
    ),
    (
        "Education",
        [r"coursera", r"udemy", r"skillshare", r"masterclass", r"chegg", r"textbook", r"tuition", r"university"],
    ),
    (
        "Income",
        [
            r"payroll", r"salary", r"direct deposit", r"paycheck", r"employer", r"interest",
            r"dividend", r"refund", r"reimbursement", r"cash back", r"deposit", r"payroll deposit",
        ],
    ),
    (
        "Transfer",
        [
            r"transfer", r"zelle", r"venmo", r"cash app", r"withdrawal", r"atm",
            r"check deposit", r"mobile deposit", r"ach", r"payment received",
        ],
    ),
]
