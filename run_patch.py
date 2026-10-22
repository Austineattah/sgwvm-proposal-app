with open('sector_logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

header = 'NEXUSVAULT AGENTIC AI ENTERPRISE PORTAL</h2>'
ack_text = 'YOUR SUBMISSION HASBEEN ACKNOWLEDGED, AWAITING ACTIVATION SHORTLY........'

if header in content:
    if 'YOUR SUBMISSION HAS BEEN ACKNOWLEDGED' not in content:
        # Inject the acknowledgment message right below the header
        target_block = header + '\n                <p style="color: #f8fafc; font-size: 1.1rem; font-weight: 500; margin-top: 15px;">YOUR SUBMISSION HAS BEEN ACKNOWLEDGED, AWAITING ACTIVATION SHORTLY........</p>'
        content = content.replace(header, target_block)
        with open('sector_logic.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully injected acknowledgement message into sector_logic.py!")
    else:
        print("Acknowledgement message is already present!")
else:
    print("Header not found.")
