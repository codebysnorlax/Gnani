from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def get_persistent_menu_keyboard() -> ReplyKeyboardMarkup:
    """Persistent reply keyboard placed in input area for language and voice persona settings."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Language / भाषा"),
                KeyboardButton(text="Voice / आवाज़"),
            ]
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Action buttons on welcome message without demo scenarios."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Choose Language / भाषा चुनें",
                    callback_data="menu:language",
                ),
                InlineKeyboardButton(
                    text="Select Voice / आवाज़ चुनें",
                    callback_data="menu:voice",
                ),
            ],
        ]
    )


def get_resume_session_keyboard() -> InlineKeyboardMarkup:
    """Keyboard prompting user whether to resume a previous incomplete dispute without emoji."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Continue Previous Case",
                    callback_data="session:resume",
                ),
                InlineKeyboardButton(
                    text="Start Fresh",
                    callback_data="session:reset",
                ),
            ],
        ]
    )


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting preferred Indic language across 10 official languages without emoji."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="हिन्दी (Hindi)", callback_data="lang:hi-IN"),
                InlineKeyboardButton(text="English", callback_data="lang:en-IN"),
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


def get_voice_character_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting verified Gnani Timbre voice characters without emoji."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Female: Shivani (Empathetic)", callback_data="voice:Shivani"),
                InlineKeyboardButton(text="Male: Devansh (Conversational)", callback_data="voice:Devansh"),
            ],
            [
                InlineKeyboardButton(text="Female: Chetana (Customer Care)", callback_data="voice:Chetana"),
            ],
        ]
    )


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Action buttons on case assessment card with accurate non-emoji labels."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Review and generate documents",
                    callback_data="action:generate_bundle",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Edit Details",
                    callback_data="action:edit_details",
                ),
                InlineKeyboardButton(
                    text="Cancel",
                    callback_data="action:cancel",
                ),
            ],
        ]
    )


def get_dossier_action_keyboard(
    whatsapp_url: str,
    twitter_url: str,
) -> InlineKeyboardMarkup:
    """Action buttons to open external deep links for NCH and X without emoji."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open NCH WhatsApp (1915)",
                    url=whatsapp_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Post on X (Twitter)",
                    url=twitter_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="File Another Dispute",
                    callback_data="action:new_dispute",
                )
            ],
        ]
    )


def get_neurons_keyboard(current_model: str | None = None) -> InlineKeyboardMarkup:
    """Keyboard for selecting Neurons OpenRouter AI model without emoji."""
    curr = current_model or "auto"

    btn_super_vl = "Nemotron 3.5 Super VL (Free)"
    if curr in ("nvidia/nemotron-3.5-super-vl:free", "super_vl"):
        btn_super_vl = "[Active] Nemotron 3.5 Super VL"

    btn_north = "North Mini Code (Free)"
    if curr in ("cohere/north-mini-code:free", "north_mini"):
        btn_north = "[Active] North Mini Code"

    btn_omni = "Nemotron 3 Nano Omni 30B (Free)"
    if curr in ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "nano_omni"):
        btn_omni = "[Active] Nemotron 3 Nano Omni 30B"

    btn_auto = "Auto (Cascade & Fallback)"
    if curr in ("auto", "", None):
        btn_auto = "[Active] Auto (Cascade & Fallback)"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=btn_super_vl,
                    callback_data="neurons:super_vl",
                )
            ],
            [
                InlineKeyboardButton(
                    text=btn_north,
                    callback_data="neurons:north_mini",
                )
            ],
            [
                InlineKeyboardButton(
                    text=btn_omni,
                    callback_data="neurons:nano_omni",
                )
            ],
            [
                InlineKeyboardButton(
                    text=btn_auto,
                    callback_data="neurons:auto",
                )
            ],
        ]
    )
