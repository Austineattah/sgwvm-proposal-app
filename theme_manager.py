class ThemeManager:
    """
    Injects custom CSS variable themes and handles client-side dynamic 10-minute rotations.
    """

    @staticmethod
    def get_theme_css(mode: str = "DEEP_BLUE") -> str:
        if mode == "SHARP_MAGENTA":
            return """
            <style>
                :root {
                    --primary-bg: #800080;
                    --accent-blue: #0000FF;
                    --card-bg: #1A001A;
                    --text-color: #FFFFFF;
                }
                body { background-color: var(--primary-bg); color: var(--text-color); }
                .stButton>button { background-color: var(--accent-blue) !important; color: white; }
            </style>
            """
        
        if mode == "DYNAMIC_10MIN":
            return """
            <style>
                @keyframes themeRotate10Min {
                    0%, 45% {
                        background-color: #000d1a;
                        color: #ffffff;
                    }
                    50%, 95% {
                        background-color: #4a004a;
                        color: #ffffff;
                    }
                    100% {
                        background-color: #000d1a;
                    }
                }
                body {
                    animation: themeRotate10Min 600s infinite ease-in-out;
                }
            </style>
            """

        return """
        <style>
            :root {
                --primary-bg: #000d1a;
                --secondary-bg: #0d0d0d;
                --accent-color: #0066cc;
                --text-color: #f2f2f2;
            }
            body { background-color: var(--primary-bg); color: var(--text-color); }
            .stSidebar { background-color: var(--secondary-bg) !important; }
        </style>
        """
