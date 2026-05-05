"""Prompts for Gemini/LLM calls."""
import json as _json


def build_tool_extraction_prompt(message: str) -> str:
    return (
        "You are an HRX assistant. Extract the HR tool and parameters from the user message below.\n"
        "Respond ONLY with a JSON object in this exact format:\n"
        "{ \"tool_name\": \"<tool_name>\", \"parameters\": { <key>: <value> } }\n\n"
        f"User message: {message}\n\n"
        "Available tools (use exact snake_case name):\n"
        "- get_attendance  : attendance records, check-in/check-out, late/on_time status\n"
        "- get_leave       : leave requests, leave types, approved/pending leave, specific employee leave\n"
        "- get_payroll_batches     : payroll batch summary, list of payroll batches by month/year\n"
        "- get_payroll_salary_sheet: employee salary details from a specific payroll batch (REQUIRES batch_id)\n\n"
        "PAYROLL TWO-STEP WORKFLOW (MANDATORY):\n"
        "1. ALWAYS for employee salary queries, use get_payroll_batches as the FIRST step (NEVER call salary_sheet directly)\n"
        "   - Extract employee name and/or month/year from message\n"
        "   - Example: 'Show Nusrat salary' → use get_payroll_batches with name='Nusrat'\n"
        "   - Example: 'Salary for Dec 2025' → use get_payroll_batches with month='2025-12'\n"
        "   - Example: 'Nusrat salary Dec 2025' → use get_payroll_batches with name='Nusrat' AND month='2025-12'\n"
        "2. The system will automatically chain to get_payroll_salary_sheet (you do NOT extract this tool)\n"
        "3. IMPORTANT: Do NOT ever call get_payroll_salary_sheet directly—it requires batch_id which only comes from batches\n\n"
        "Parameter extraction rules:\n"
        "- For ATTENDANCE queries, extract these parameters:\n"
        "  * name: employee name (e.g., 'Shanto', 'Tamim', 'Abdul Miah')\n"
        "  * date: specific date in YYYY-MM-DD format or month in YYYY-MM format\n"
        "  * month: month for attendance filtering (e.g., '2026-02', '02', 'February')\n"
        "  * year: year for attendance filtering (e.g., '2026', '26')\n"
        "  * checkInStatus: attendance status (late, on time, absent, etc.)\n"
        "  * checkInTime: check-in time for filtering (e.g., 'after 9', '9am', '09:00')\n"
        "  * checkOutTime: check-out time for filtering (e.g., 'before 5', '5pm', '17:00')\n"
        "  Examples:\n"
        "    'give Shanto attendance' → {\"name\": \"Shanto\"}\n"
        "    'attendance for Shanto late' → {\"name\": \"Shanto\", \"checkInStatus\": \"late\"}\n"
        "    'Shanto late February 2026' → {\"name\": \"Shanto\", \"checkInStatus\": \"late\", \"month\": \"2026-02\"}\n"
        "    'attendance after 9am' → {\"checkInTime\": \"after 9am\"}\n"
        "    'Shanto attendance checkin after 9' → {\"name\": \"Shanto\", \"checkInTime\": \"after 9\"}\n"
        "    'late attendance before 5pm' → {\"checkInStatus\": \"late\", \"checkOutTime\": \"before 5pm\"}\n\n"
        "- For LEAVE queries, extract these parameters:\n"
        "  * name: employee name\n"
        "  * leaveType: type of leave (Annual, Casual, Unpaid, Sick, etc.)\n"
        "  * status: leave status (APPROVED, PENDING, REJECTED, etc.)\n"
        "  * month: month for filtering (e.g., '2026-02', 'February')\n"
        "  * year: year for filtering\n"
        "  Examples:\n"
        "    'Shanto sick leave' → {\"name\": \"Shanto\", \"leaveType\": \"Sick\"}\n"
        "    'approved casual leave March 2026' → {\"leaveType\": \"Casual\", \"status\": \"APPROVED\", \"month\": \"2026-03\"}\n\n"
        "- For PAYROLL queries, extract these parameters:\n"
        "  * name: employee name (e.g., 'Nusrat', 'Shanto', 'Abdul Miah')\n"
        "  * status: payment status (PAID, UNPAID, etc.)\n"
        "  * month: month for filtering (e.g., '2026-03', 'March')\n"
        "  * year: year for filtering (e.g., '2026')\n"
        "  * department: department name (e.g., 'IT', 'HR', 'Finance')\n"
        "  Examples:\n"
        "    'Nusrat salary' → {\"name\": \"Nusrat\"}\n"
        "    'unpaid salary March 2026' → {\"status\": \"UNPAID\", \"month\": \"2026-03\"}\n"
        "    'IT department salary list' → {\"department\": \"IT\"}\n"
        "    'Shanto unpaid salary March' → {\"name\": \"Shanto\", \"status\": \"UNPAID\", \"month\": \"2026-03\"}\n\n"
        "- For date ranges use startDate and endDate in YYYY-MM-DD format.\n"
        "- For month-based queries use month in YYYY-MM format (e.g., '2025-12' for December 2025, 'dec 2025', '12/2025').\n"
        "- For employee-specific queries (e.g., 'Shanto-র attendance', 'Nusrat leave', 'John attendance'):\n"
        "  Extract the employee name EXACTLY as mentioned and use 'name' parameter.\n"
        "  Examples: {\"name\": \"Shanto\"}, {\"name\": \"Nusrat\"}, {\"name\": \"Abdul Miah\"}, {\"name\": \"John Doe\"}\n"
        "- For COMBINED queries (employee + month/year + status), extract ALL:\n"
        "  Examples:\n"
        "  'Show Shanto attendance February late' → {\"name\": \"Shanto\", \"month\": \"2026-02\", \"checkInStatus\": \"late\"}\n"
        "  'Shanto late checkin after 9 February' → {\"name\": \"Shanto\", \"checkInStatus\": \"late\", \"checkInTime\": \"after 9\", \"month\": \"2026-02\"}\n"
        "  'December 2025 Shanto sick leave approved' → {\"name\": \"Shanto\", \"leaveType\": \"Sick\", \"status\": \"APPROVED\", \"month\": \"2025-12\"}\n"
        "- For leave type filters (Annual, Casual, Unpaid): use 'leaveType' parameter.\n"
        "- For status filters (APPROVED, PENDING, REJECTED, late, on time, absent): use 'status' parameter or 'checkInStatus' for attendance.\n"
        "- Page/pageSize parameters are handled by system (default page=1, pageSize=10).\n"
        "- If user asks for a date range: include both startDate and endDate.\n"
        "- If no specific tool matches, set tool_name to empty string.\n"
        "IMPORTANT NOTES:\n"
        "1. When extracting employee names, preserve spelling, capitalization, and transliteration exactly.\n"
        "2. For Bengali queries with '-র or এর patterns (possessive), extract the name before the pattern.\n"
        "3. Names can be single word (Shanto) or multiple words (Abdul Miah, John Doe).\n"
        "4. Always check if 'name' parameter appears in the message - if yes, include it.\n"
        "5. Always check if 'month', 'year', or status keywords appear in the message - if yes, extract and include them.\n"
        "6. For attendance queries, ALWAYS extract checkInStatus if status words like 'late', 'on time', 'absent' appear.\n"
        "7. For time-based attendance filtering, extract checkInTime or checkOutTime if mentioned.\n"
        "8. CRITICAL: For salary queries WHERE [employee seeks their own salary], ALWAYS use get_payroll_batches (never salary_sheet)\n"
        "Output ONLY the JSON, no explanation."
    )


def build_answer_prompt(user_message: str, tool_name: str, data) -> str:
    """Prompt to convert raw HRX API data into a natural language answer."""
    data_str = _json.dumps(data, ensure_ascii=False, indent=2)
    
    # Build base instructions
    base_instructions = (
        "- Keep it concise and human-readable.\n"
        "- Do NOT mention JSON, API, or technical details.\n"
        "- Respond in the same language the user used.\n"
        "- If no records found, politely inform the user.\n"
    )
    
    # Add tool-specific instructions
    tool_specific = ""
    if tool_name == "get_leave":
        tool_specific = (
            "- This is a LEAVE request query.\n"
            "- For each employee's leave record, clearly show: Employee Name | Leave Type | Dates | Number of Days | Status.\n"
            "- If user asked about a SPECIFIC employee's leave, group all their leaves and provide a summary.\n"
            "- Show leaves in chronological order (earliest date first).\n"
            "- If user asked about leave types or status filters, highlight those clearly.\n"
            "- For multiple employees, show one paragraph per employee with key details.\n"
            "- IMPORTANT: Extract and prominently display employee NAMES from the data.\n"
        )
    elif tool_name == "get_attendance":
        tool_specific = (
            "- This is an ATTENDANCE record query.\n"
            "- For each record, clearly show: Date | Employee Name | Check-in Time | Check-out Time | Status (on-time/late).\n"
            "- If user asked about a SPECIFIC employee, focus on their attendance summary.\n"
            "- Group by date or employee as appropriate.\n"
            "- Highlight if there are patterns (e.g., multiple late arrivals, absences).\n"
        )
    elif tool_name == "get_payroll_batches":
        tool_specific = (
            "- This is a PAYROLL BATCH LIST query.\n"
            "- Display batch summaries: Batch Name | Month/Year | Total Employees | Total Amount | Status.\n"
            "- Sort by date (most recent first).\n"
            "- If user specified a month/year, highlight matching batches.\n"
            "- Note: This is the first step to get batch_id for salary details.\n"
        )
    elif tool_name == "get_payroll_salary_sheet":
        tool_specific = (
            "- This is a PAYROLL SALARY SHEET query (employee salary details within a batch).\n"
            "- For each employee, show: Employee Name | Employee ID | Department | Net Salary | Status.\n"
            "- If user asked about a SPECIFIC employee, focus on their salary record.\n"
            "- Show gross salary, deductions, and final net payment clearly.\n"
            "- Include payment date if available.\n"
        )
    elif tool_name == "get_payroll":
        tool_specific = (
            "- This is a PAYROLL record query.\n"
            "- For each payroll record, show: Employee Name | Month | Basic Salary | Deductions | Net Payable.\n"
            "- If user asks about salary, focus on net payable amount.\n"
        )
    
    return (
        "You are a helpful HRX (HR Management) assistant.\n"
        "A user asked a question and the HR system returned the following data.\n"
        "Your job is to summarize this data in a clear, friendly, and professional way based on what the user asked.\n\n"
        f"User question: {user_message}\n\n"
        f"HR Tool used: {tool_name}\n\n"
        f"Data returned from HR system:\n{data_str}\n\n"
        "Instructions:\n"
        "- Summarize the key information the user needs.\n"
        + tool_specific +
        base_instructions +
        "Answer:"
    )



def build_out_of_scope_prompt(user_message: str) -> str:
    """Prompt to politely decline out-of-scope or irrelevant questions."""
    return (
        "You are a professional HRX (HR Management) assistant.\n"
        "You are ONLY capable of helping with HR-related topics such as:\n"
        "attendance, leave, payroll, employee records, shifts, and similar HR modules.\n\n"
        f"The user sent the following message: {user_message}\n\n"
        "This message does NOT relate to any HR topic you can handle.\n"
        "Write a short, polite, and professional response explaining that:\n"
        "- You are an HRX assistant and can only help with HR-related questions.\n"
        "- You are not able to assist with this particular request.\n"
        "- Suggest what kinds of questions you CAN help with (attendance, leave, payroll, etc.).\n"
        "- Respond in the same language the user used.\n"
        "Keep it to 2-3 sentences maximum.\n"
        "Response:"
    )


def build_audio_transcription_prompt() -> str:
    """Prompt for audio transcription task."""
    return (
        "Please transcribe the following audio file. Return only the transcribed text without any additional commentary."
    )


def build_similarity_calculation_prompt(text1: str, text2: str) -> str:
    """Prompt for calculating similarity between two texts.
    
    Args:
        text1: Original script
        text2: Transcribed text
        
    Returns:
        Formatted prompt for Gemini
    """
    return f"""Compare the following two texts and provide a similarity percentage (0-100).
            
Original Script:
{text1}

Transcribed Text:
{text2}

Respond with ONLY a JSON object in this format:
{{"similarity_percentage": <number between 0 and 100>, "notes": "<brief explanation>"}}

Do not include any markdown formatting or code blocks. Just the JSON object."""
