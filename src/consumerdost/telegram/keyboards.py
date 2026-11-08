from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Buttons on welcome message offering 1-tap demo prompts, Prisma showcases, and language selection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Demo: Flipkart Broken Phone",
                    callback_data="demo:flipkart",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Demo: UPI Failed ₹1,200 Recharge",
                    callback_data="demo:upi",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✈️ Demo: Cancelled Flight Refund",
                    callback_data="demo:flight",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Prisma Showcase: Street Noise Audio",
                    callback_data="demo:noisy",
                ),
                InlineKeyboardButton(
                    text="🗣️ Prisma Showcase: Hinglish Code-Mixed",
                    callback_data="demo:codemixed",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Choose Language / भाषा चुनें",
                    callback_data="menu:language",
                )
            ],
        ]
    )


def get_resume_session_keyboard() -> InlineKeyboardMarkup:
    """Keyboard prompting user whether to resume a previous incomplete dispute."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ Continue Previous Case",
                    callback_data="session:resume",
                ),
                InlineKeyboardButton(
                    text="🔄 Start Fresh",
                    callback_data="session:reset",
                ),
            ],
        ]
    )



def get_language_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting preferred Indic language across 10 official languages."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇮🇳 हिन्दी (Hindi)", callback_data="lang:hi-IN"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en-IN"),
            ],
            [
                InlineKeyboardButton(text="ಕನ್ನಡ (Kannada)", callback_data="lang:kn-IN"),
                InlineKeyboardButton(text="தமிழ் (Tamil)", callback_data="lang:ta-IN"),
            ],
            [
                InlineKeyboardButton(text="తెలుగు (Telugu)", callback_data="lang:te-IN"),
                InlineKeyboardButton(text="मराठी (Marathi)", callback_data="lang:mr-IN"),
            ],
            [
                InlineKeyboardButton(text="বাংলা (Bengali)", callback_data="lang:bn-IN"),
                InlineKeyboardButton(text="ગુજરાતી (Gujarati)", callback_data="lang:gu-IN"),
            ],
            [
                InlineKeyboardButton(text="മലയാളം (Malayalam)", callback_data="lang:ml-IN"),
                InlineKeyboardButton(text="ਪੰਜਾਬੀ (Punjabi)", callback_data="lang:pa-IN"),
            ],
        ]
    )


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Action buttons on case assessment card."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Generate Full Escalation Bundle",
                    callback_data="action:generate_bundle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Edit Details",
                    callback_data="action:edit_details",
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="action:cancel",
                ),
            ],
        ]
    )


def get_dossier_action_keyboard(
    whatsapp_url: str,
    twitter_url: str,
) -> InlineKeyboardMarkup:
    """Action buttons to open external deep links for NCH and X."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Open NCH WhatsApp (1915)",
                    url=whatsapp_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🐦 Post on X (Twitter)",
                    url=twitter_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 File Another Dispute",
                    callback_data="action:new_dispute",
                )
            ],
        ]
    )
