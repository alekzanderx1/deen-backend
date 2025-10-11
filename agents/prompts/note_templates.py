# =============================================================================
# NOTE TEMPLATES AND EXAMPLES
# =============================================================================

# These templates provide guidance for consistent note formatting across different categories

NOTE_CATEGORIES = {
    "learning_notes": {
        "description": "What the user has studied, learned, or is currently learning",
        "examples": [
            "User completed basic prayer lesson and shows good understanding of wudu requirements",
            "Currently learning about Imamate - has grasped the concept of divine appointment but struggles with historical succession details",
            "Shows strong interest in studying Nahj al-Balagha and quotes from Imam Ali"
        ]
    },
    
    "knowledge_notes": {
        "description": "What the user knows well vs. areas where they lack knowledge",
        "examples": [
            "Strong foundational knowledge of the Five Pillars but unfamiliar with Shia-specific practices",
            "Knows basic Islamic history but has knowledge gaps about the role of Imam Hussain at Karbala",
            "Well-versed in Quranic recitation but needs more understanding of Shia interpretation methods"
        ]
    },
    
    "interest_notes": {
        "description": "Topics, themes, or aspects of Islam that particularly engage the user",
        "examples": [
            "Shows deep fascination with the philosophical teachings of Imam Ali",
            "Frequently asks about the role of women in early Islamic history, particularly Lady Fatimah",
            "Very interested in understanding differences between Shia and Sunni interpretations"
        ]
    },
    
    "behavior_notes": {
        "description": "Learning patterns, interaction styles, and behavioral observations",
        "examples": [
            "Prefers detailed explanations with historical context rather than brief answers",
            "Often asks follow-up questions showing genuine curiosity to deepen understanding",
            "Tends to connect new concepts to previous knowledge, indicating analytical learning style"
        ]
    },
    
    "preference_notes": {
        "description": "User preferences for learning style, content depth, language, etc.",
        "examples": [
            "Prefers content that includes both Arabic terms and English explanations",
            "Likes when lessons include practical applications to daily life",
            "Shows preference for scholarly sources and authentic hadith references"
        ]
    }
}

# =============================================================================
# SHIA-SPECIFIC GUIDANCE FOR NOTES
# =============================================================================

SHIA_PERSPECTIVE_GUIDANCE = {
    "recommended_topics": [
        "The Twelve Imams and their teachings",
        "Ahl al-Bayt and their significance",
        "The event of Ghadir Khum",
        "Karbala and Imam Hussain's sacrifice",
        "Lady Fatimah's role and status",
        "Shia interpretation of the Quran",
        "The concept of Wilayah",
        "Imamate as divine appointment",
        "Shia hadith collections (Kutub al-Arba'a)",
        "The philosophy of Imam Ali",
        "Mourning practices (Muharram/Ashura)",
        "Contemporary Shia scholarship"
    ],
    
    "topics_to_approach_carefully": [
        "Differences with Sunni Islam (present respectfully, focus on Shia perspective)",
        "Historical controversies (focus on Shia understanding)",
        "Companion narratives (prioritize Ahl al-Bayt perspective)",
    ],
    
    "topics_to_avoid_recommending": [
        "Praise of figures opposed to Ahl al-Bayt in Shia perspective",
        "Sunni-specific practices that conflict with Shia beliefs",
        "Historical narratives that contradict core Shia principles"
    ]
}

# =============================================================================
# NOTE QUALITY GUIDELINES
# =============================================================================

NOTE_QUALITY_CRITERIA = {
    "good_notes": {
        "characteristics": [
            "Specific and actionable",
            "Based on clear evidence from interaction",
            "Helps with future personalization",
            "Avoids assumptions or overgeneralization",
            "Focuses on learning-relevant information"
        ],
        "examples": [
            "✅ User asked three separate questions about Imam Ali's governance, showing interest in political philosophy",
            "✅ Struggled to understand the concept of 'Raj'a' despite detailed explanation, may need foundational theological concepts first",
            "✅ Prefers when Arabic terms are explained with etymology and pronunciation guides"
        ]
    },
    
    "poor_notes": {
        "characteristics": [
            "Too vague or general",
            "Based on single interaction without pattern",
            "Not actionable for personalization",
            "Makes assumptions about user's background",
            "Focuses on irrelevant details"
        ],
        "examples": [
            "❌ User seems interested in Islam",
            "❌ Asked a question about prayer",
            "❌ Appears to be a beginner"
        ]
    }
}

# =============================================================================
# CONSOLIDATION STRATEGIES
# =============================================================================

CONSOLIDATION_STRATEGIES = {
    "merge_similar": {
        "description": "Combine notes that express the same insight",
        "example": {
            "before": [
                "User enjoys learning about Imam Ali's sayings",
                "Shows interest in Nahj al-Balagha quotes",
                "Frequently asks about Imam Ali's wisdom"
            ],
            "after": "User has strong interest in Imam Ali's teachings and wisdom, particularly from Nahj al-Balagha"
        }
    },
    
    "elevate_patterns": {
        "description": "Create higher-level insights from multiple observations",
        "example": {
            "before": [
                "Asks for historical context with each theological concept",
                "Prefers explanations that connect to contemporary issues",
                "Likes when lessons include practical applications"
            ],
            "after": "User has analytical learning style - prefers comprehensive understanding that connects historical Islamic teachings to practical modern applications"
        }
    },
    
    "remove_outdated": {
        "description": "Remove notes that are no longer relevant",
        "criteria": [
            "Contradicted by more recent observations",
            "Based on initial interactions that may not represent true patterns",
            "No longer relevant due to user's learning progression"
        ]
    }
}
