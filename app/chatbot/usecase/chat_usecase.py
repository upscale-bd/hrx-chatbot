from sqlalchemy.orm import Session
from datetime import datetime
import re
from app.chatbot.dto.chat_dto import ChatRequest, ChatResponse, ChatResponseData, ToolInfo, ReportInfo
from app.chatbot.repository.chat_repository import create_chat_entry, update_chat_response
from services.gemini.gemini_service import GeminiService
from services.mcp.executor import MCPExecutor
from services.report.report_service import ReportService
from common.logger import get_logger


logger = get_logger("chat_usecase")


def _markdown_to_plain(text: str) -> str:
    """Convert markdown text to plain text by removing markdown formatting."""
    if not text:
        return text
    
    # Remove bold/italic (**text** -> text, *text* -> text, __text__ -> text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # Remove links [text](url) -> text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    
    # Remove headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove bullet points but keep content
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    
    # Clean up extra whitespace
    text = re.sub(r'\n\n+', '\n', text)
    text = text.strip()
    
    return text


def _time_filter_match(record: dict, field_name: str, time_query: str) -> bool:
    """Check if a record matches time filter criteria.
    Supports: "9", "9:00", "9am", "after 9", "before 5pm", etc.
    """
    time_query = time_query.strip().lower()
    comparison = "after"  # default
    
    # Check for before/after keywords
    if time_query.startswith("before "):
        comparison = "before"
        time_query = time_query.replace("before ", "").strip()
    elif time_query.startswith("after "):
        comparison = "after"
        time_query = time_query.replace("after ", "").strip()
    
    # Extract hour and minute
    hour = None
    minute = 0
    
    # Handle "9am", "9pm" format
    if "am" in time_query or "pm" in time_query:
        is_pm = "pm" in time_query
        time_part = time_query.replace("am", "").replace("pm", "").strip()
        if ":" in time_part:
            parts = time_part.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        else:
            hour = int(time_part)
        if is_pm and hour != 12:
            hour += 12
        elif not is_pm and hour == 12:
            hour = 0
    # Handle "HH:MM" or "H" format
    elif ":" in time_query:
        parts = time_query.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    else:
        # Just a number like "9"
        hour = int(time_query)
    
    if hour is None:
        return True  # Allow on parse error
    
    target_time = f"{hour:02d}:{minute:02d}"
    
    # Extract time from record
    time_str = str(record.get(field_name, "")).strip()
    if not time_str:
        return False  # No time value, exclude
    
    # Extract time from ISO format: "2026-02-10T16:30:03.550Z" -> "16:30"
    if "T" in time_str:
        time_part = time_str.split("T")[1]  # "16:30:03.550Z"
        time_part = time_part.split(".")[0]  # "16:30:03"
        time_part = time_part[:5]  # "16:30"
    else:
        time_part = time_str[:5]  # First 5 chars
    
    # Compare times
    try:
        if comparison == "after":
            return time_part >= target_time
        else:  # before
            return time_part <= target_time
    except Exception:
        return True  # Allow on error


class ChatUsecase:
    def __init__(self, db: Session):
        logger.info("[chat_usecase] Initializing ChatUsecase")
        self.db = db
        self.gemini = GeminiService()
        self.mcp = MCPExecutor(db)
        self.report_service = ReportService(db=db)  # Pass DB to ReportService
        logger.info("[chat_usecase] GeminiService, MCPExecutor, ReportService initialized")

    def handle_message(self, req: ChatRequest, organization_id: str) -> ChatResponse:
        import time
        start_time = time.time()
        logger.info(f"[chat_usecase] handle_message start | org={organization_id}")
        chat_entry = None
        tool_name = ""
        tool_endpoint = ""
        tool_status = "not_used"
        records_count = 0

        # 1. Persist incoming message immediately
        logger.info("[chat_usecase] Step 1 — persisting chat entry to DB")
        try:
            chat_entry = create_chat_entry(self.db, organization_id, req.message)
            logger.info(f"[chat_usecase] Chat entry created | id={chat_entry.id}")
        except Exception as exc:
            logger.error(f"[chat_usecase] Step 1 failed — DB write error: {exc}")
            return ChatResponse(
                success=False,
                status="error",
                data=None,
                error="Database error occurred. Please try again."
            )

        # 2. Extract tool + parameters via Gemini
        logger.info("[chat_usecase] Step 2 — calling Gemini to extract tool from message")
        try:
            tool_data = self.gemini.extract_tool(req.message)
            tool_name = tool_data.get("tool_name", "")
            logger.info(
                f"[chat_usecase] Gemini extracted | tool_name='{tool_name}' | parameters={tool_data.get('parameters')}"
            )
        except Exception as exc:
            logger.error(f"[chat_usecase] Step 2 failed — Gemini extraction error: {exc}")
            tool_data = {"tool_name": "", "parameters": {}}

        # 3. Out-of-scope check — if Gemini couldn't identify any HR tool
        if not tool_name:
            logger.warning("[chat_usecase] No tool extracted — treating as out-of-scope")
            try:
                answer = self.gemini.handle_out_of_scope(req.message)
            except Exception as exc:
                logger.error(f"[chat_usecase] handle_out_of_scope failed: {exc}")
                answer = "I'm an HRX assistant and can only help with HR-related topics such as attendance, leave, and payroll."
            try:
                update_chat_response(self.db, chat_entry.id, answer)
            except Exception as exc:
                logger.error(f"[chat_usecase] Failed to save out-of-scope response: {exc}")
            
            response_time = f"{time.time() - start_time:.2f}s"
            logger.info(f"[chat_usecase] handle_message complete (out-of-scope) | time={response_time}")
            return ChatResponse(
                success=True,
                status="out_of_scope",
                data=ChatResponseData(
                    chatId=chat_entry.id,
                    answer=_markdown_to_plain(answer),
                    answerMarkdown=answer,
                    toolUsed=ToolInfo(name=None, status="not_used"),
                    report=None,
                    metadata={"responseTime": response_time}
                ),
                error=None
            )

        # 4. Execute tool via MCP
        logger.info(f"[chat_usecase] Step 4 — executing tool via MCP | tool='{tool_name}'")
        try:
            tool_response = self.mcp.execute_tool(
                tool_name=tool_name,
                parameters=tool_data["parameters"],
                organization_id=organization_id,
            )
            tool_status = "success"
            logger.info(
                f"[chat_usecase] MCP response type={type(tool_response).__name__} | is_list={isinstance(tool_response, list)}"
            )
        except Exception as exc:
            logger.error(f"[chat_usecase] Step 4 failed — MCP executor error: {exc}")
            tool_response = {"error": str(exc)}
            tool_status = "failed"

        # 4.5 Auto-chain: If tool is get_payroll_batches and user mentioned salary details, fetch salary sheet
        if tool_name == "get_payroll_batches" and tool_status == "success" and isinstance(tool_response, list):
            # Check if user asked for salary details (name, department, or month filter)
            employee_name = tool_data.get("parameters", {}).get("name", "").strip()
            department = tool_data.get("parameters", {}).get("department", "").strip()
            month_filter = str(tool_data.get("parameters", {}).get("month", "")).strip()
            
            # Auto-chain if: has name, OR has department, OR has month filter
            should_auto_chain = employee_name or department or month_filter
            
            if should_auto_chain and tool_response:
                logger.info(
                    f"[chat_usecase] Auto-chaining to salary sheet | "
                    f"name={employee_name} dept={department} month={month_filter}"
                )

                # Build candidate batch list and prioritize recent batches first.
                # If month filter exists (YYYY-MM), prefer matching batches only.
                target_year = None
                target_month = None
                if month_filter and "-" in month_filter:
                    parts = month_filter.split("-", 1)
                    if len(parts) == 2:
                        target_year, target_month = parts[0], parts[1].lstrip("0") or "0"

                candidates = [b for b in tool_response if isinstance(b, dict) and b.get("id")]
                if target_year and target_month:
                    filtered_candidates = []
                    for batch in candidates:
                        year_val = str(batch.get("year", "")).strip()
                        month_val = str(batch.get("month", "")).strip().lstrip("0") or "0"
                        if year_val == target_year and month_val == target_month:
                            filtered_candidates.append(batch)
                    if filtered_candidates:
                        candidates = filtered_candidates
                        logger.info(
                            f"[chat_usecase] Auto-chain: Month filter matched {len(candidates)} batch(es) for {month_filter}"
                        )

                # Prioritize PAID batches first, then latest year/month.
                def _batch_sort_key(batch: dict):
                    status_val = str(batch.get("status", "")).strip().upper()
                    is_paid = 1 if status_val == "PAID" else 0
                    try:
                        y = int(str(batch.get("year", 0) or 0))
                    except Exception:
                        y = 0
                    try:
                        m = int(str(batch.get("month", 0) or 0))
                    except Exception:
                        m = 0
                    return (is_paid, y, m)

                candidates.sort(key=_batch_sort_key, reverse=True)

                if not candidates:
                    logger.warning("[chat_usecase] Auto-chain: No candidate batch_id found in response")
                else:
                    logger.info(f"[chat_usecase] Auto-chain: Trying {len(candidates)} candidate batch(es)")
                    found_salary = False
                    all_salary_records = []  # Collect from all batches
                    for idx, batch in enumerate(candidates, start=1):
                        batch_id = batch.get("id")
                        logger.info(
                            f"[chat_usecase] Auto-chain: Attempt {idx}/{len(candidates)} | "
                            f"batch_id={batch_id} year={batch.get('year')} month={batch.get('month')}"
                        )
                        try:
                            # Build salary sheet parameters with all filters
                            salary_params = {"batch_id": batch_id}
                            if employee_name:
                                salary_params["name"] = employee_name
                            if department:
                                salary_params["department"] = department
                            
                            salary_response = self.mcp.execute_tool(
                                tool_name="get_payroll_salary_sheet",
                                parameters=salary_params,
                                organization_id=organization_id,
                            )
                            if isinstance(salary_response, list) and len(salary_response) > 0:
                                logger.info(
                                    f"[chat_usecase] Auto-chain: Found {len(salary_response)} salary records "
                                    f"in batch_id={batch_id}"
                                )
                                all_salary_records.extend(salary_response)
                                found_salary = True
                            elif isinstance(salary_response, dict) and salary_response.get("error"):
                                logger.warning(
                                    f"[chat_usecase] Auto-chain: Salary sheet error for batch_id={batch_id} | "
                                    f"error={salary_response.get('error')}"
                                )
                        except Exception as exc:
                            logger.error(f"[chat_usecase] Auto-chain attempt failed for batch_id={batch_id}: {exc}")

                    if found_salary and all_salary_records:
                        logger.info(
                            f"[chat_usecase] Auto-chain: Merged {len(all_salary_records)} total salary records "
                            f"from {len(candidates)} batch(es)"
                        )
                        tool_response = all_salary_records
                        tool_name = "get_payroll_salary_sheet"
                    else:
                        logger.info("[chat_usecase] Auto-chain: No salary records found in candidate batches; keeping batch list")

        # 5. Generate report if there is list data
        data_list = tool_response if isinstance(tool_response, list) else []
        
        # Apply client-side filters: name, leave_type, month, year, status, checkInStatus, checkInTime, checkOutTime, etc.
        # This ensures the report only contains data matching user's search criteria
        search_params = tool_data.get("parameters", {})
        search_name = search_params.get("name")
        search_leave_type = search_params.get("leaveType") or search_params.get("leave_type")
        search_status = search_params.get("status")
        search_check_in_status = search_params.get("checkInStatus")
        search_check_in_time = search_params.get("checkInTime")
        search_check_out_time = search_params.get("checkOutTime")
        search_month = search_params.get("month")
        search_year = search_params.get("year")
        
        # Apply active filters
        if (search_name or search_leave_type or search_status or search_check_in_status or search_check_in_time or search_check_out_time or search_month or search_year) and isinstance(data_list, list) and len(data_list) > 0:
            filtered_by_criteria = []
            
            for record in data_list:
                if not isinstance(record, dict):
                    continue
                
                # Check name filter
                if search_name:
                    search_name_lower = search_name.strip().lower()
                    found_name = False
                    for name_field in ["name", "employee_name", "emp_name", "full_name"]:
                        record_name = str(record.get(name_field, "")).strip().lower()
                        if record_name and search_name_lower in record_name:
                            found_name = True
                            break
                    if not found_name:
                        continue
                
                # Check leave type filter
                if search_leave_type:
                    search_type_lower = search_leave_type.strip().lower()
                    leave_type_field = record.get("leaveType") or record.get("leave_type") or record.get("type")
                    record_leave_type = str(leave_type_field or "").strip().lower()
                    if not record_leave_type or search_type_lower not in record_leave_type:
                        continue
                
                # Check status filter (checks both 'status' for leaves and 'checkInStatus' for attendance)
                if search_status:
                    search_status_lower = search_status.strip().lower()
                    record_status = str(record.get("status", "")).strip().lower()
                    record_check_in_status = str(record.get("checkInStatus", "")).strip().lower()
                    status_match = search_status_lower in record_status or search_status_lower in record_check_in_status
                    if not status_match:
                        continue
                
                # Check checkInStatus filter (for attendance records - late, on time, absent, etc.)
                if search_check_in_status:
                    search_check_status_lower = search_check_in_status.strip().lower()
                    record_check_status = str(record.get("checkInStatus", "")).strip().lower()
                    if not record_check_status or search_check_status_lower not in record_check_status:
                        continue
                
                # Check checkInTime filter (attendance time after/before specific time)
                if search_check_in_time:
                    if not self._time_filter_match(record, "checkInTime", search_check_in_time):
                        continue
                
                # Check checkOutTime filter (attendance time after/before specific time)
                if search_check_out_time:
                    if not self._time_filter_match(record, "checkOutTime", search_check_out_time):
                        continue
                
                # Check month filter - handle flexible formats (2026-03, 03, 3, March, march)
                # Also extract from date fields if direct month field not present
                if search_month:
                    record_month = str(record.get("month") or record.get("Month") or "").strip()
                    
                    # If no direct month field, try to extract from date fields
                    if not record_month:
                        for date_field in ["start_date", "date", "end_date", "applied_at"]:
                            date_str = str(record.get(date_field, "")).strip()
                            if date_str and len(date_str) >= 7:  # At least "2026-02"
                                try:
                                    # Extract MM from "2026-02-15T00:00:00.000Z"
                                    record_month = date_str[5:7]  # Get "02"
                                    break
                                except Exception:
                                    pass
                    
                    if record_month:
                        # Normalize record month to 1 or 2 digit format
                        record_month_norm = record_month.lstrip("0") or "0"
                        
                        # Normalize search month (handle "2026-03", "03", "3", "march")
                        month_map = {
                            "january": "1", "february": "2", "march": "3", "april": "4",
                            "may": "5", "june": "6", "july": "7", "august": "8",
                            "september": "9", "october": "10", "november": "11", "december": "12"
                        }
                        
                        search_month_norm = search_month.strip()
                        if "-" in search_month_norm:  # "2026-03" format
                            parts = search_month_norm.split("-", 1)
                            if len(parts) == 2:
                                search_month_norm = parts[1].lstrip("0") or "0"
                        elif search_month_norm.isdigit():  # "03" or "3" format
                            search_month_norm = search_month_norm.lstrip("0") or "0"
                        else:  # Month name like "march"
                            search_month_norm = month_map.get(search_month_norm.lower(), search_month_norm)
                        
                        if record_month_norm != search_month_norm:
                            continue
                    else:
                        continue
                
                # Check year filter - handle flexible formats (2026, 26)
                # Also extract from date fields if direct year field not present
                if search_year:
                    record_year = str(record.get("year") or record.get("Year") or "").strip()
                    
                    # If no direct year field, try to extract from date fields
                    if not record_year:
                        for date_field in ["start_date", "date", "end_date", "applied_at"]:
                            date_str = str(record.get(date_field, "")).strip()
                            if date_str and len(date_str) >= 4:
                                try:
                                    # Extract YYYY from "2026-02-15T00:00:00.000Z"
                                    record_year = date_str[:4]
                                    break
                                except Exception:
                                    pass
                    
                    if record_year:
                        # Normalize search year (handle "2026" or "26")
                        search_year_norm = search_year.strip()
                        if search_year_norm.isdigit() and len(search_year_norm) == 2:
                            y = int(search_year_norm)
                            search_year_norm = str(2000 + y) if y <= 30 else str(1900 + y)
                        
                        if record_year != search_year_norm:
                            continue
                    else:
                        continue
                
                # All filter criteria passed
                filtered_by_criteria.append(record)
            
            if filtered_by_criteria:
                before_count = len(data_list)
                data_list = filtered_by_criteria
                filter_desc = []
                if search_name:
                    filter_desc.append(f"name='{search_name}'")
                if search_leave_type:
                    filter_desc.append(f"leave_type='{search_leave_type}'")
                if search_status:
                    filter_desc.append(f"status='{search_status}'")
                if search_check_in_status:
                    filter_desc.append(f"checkInStatus='{search_check_in_status}'")
                if search_check_in_time:
                    filter_desc.append(f"checkInTime='{search_check_in_time}'")
                if search_check_out_time:
                    filter_desc.append(f"checkOutTime='{search_check_out_time}'")
                if search_month:
                    filter_desc.append(f"month='{search_month}'")
                if search_year:
                    filter_desc.append(f"year='{search_year}'")
                logger.info(f"[chat_usecase] Applied multi-criteria filter | {', '.join(filter_desc)} | before={before_count} after={len(data_list)}")
            else:
                filter_desc = []
                if search_name:
                    filter_desc.append(f"name='{search_name}'")
                if search_leave_type:
                    filter_desc.append(f"leave_type='{search_leave_type}'")
                if search_status:
                    filter_desc.append(f"status='{search_status}'")
                if search_check_in_status:
                    filter_desc.append(f"checkInStatus='{search_check_in_status}'")
                if search_check_in_time:
                    filter_desc.append(f"checkInTime='{search_check_in_time}'")
                if search_check_out_time:
                    filter_desc.append(f"checkOutTime='{search_check_out_time}'")
                if search_month:
                    filter_desc.append(f"month='{search_month}'")
                if search_year:
                    filter_desc.append(f"year='{search_year}'")
                logger.warning(f"[chat_usecase] Multi-criteria filter found no matches | {', '.join(filter_desc)} | keeping all data")
        
        # Filter out records with "Unknown" in the name field (main identifier)
        if isinstance(data_list, list):
            data_list = [
                record for record in data_list
                if isinstance(record, dict) and 
                record.get('name', '').strip().lower() != 'unknown'
            ]
            logger.info(f"[chat_usecase] Filtered Unknown name records | remaining={len(data_list)}")
            
            # Replace "Unknown" strings with professional message in all fields
            for record in data_list:
                if isinstance(record, dict):
                    for key, value in record.items():
                        if isinstance(value, str) and value.strip().lower() == 'unknown':
                            record[key] = 'Not available'
                        elif isinstance(value, str) and 'unknown' in value.lower():
                            # Replace "Unknown was" with "Employee"
                            record[key] = value.replace('Unknown', 'Employee').replace('unknown', 'Employee')
            logger.info("[chat_usecase] Replaced 'Unknown' strings with professional messages")
        
        records_count = len(data_list)
        logger.info(f"[chat_usecase] Step 5 — generating report | records={records_count}")
        report_id = None
        report_url = None
        try:
            # Set exclude patterns based on tool type
            exclude_patterns = ['id', '_id', 'uuid', 'Id', 'photo', 'image', 'url', 'link']
            
            # For attendance reports, also exclude summary and employee_name
            if tool_name.lower() == 'get_attendance':
                exclude_patterns.extend(['summary', 'employee_name', 'emp_name'])
                logger.info("[chat_usecase] Attendance tool detected - excluding summary and employee_name")
            
            # For leave reports, exclude created_at, updated_at, approver, employee
            elif tool_name.lower() == 'get_leave':
                exclude_patterns.extend(['created_at', 'updated_at', 'approver', 'createdAt', 'updatedAt', 'employee', 'employee_info'])
                logger.info("[chat_usecase] Leave tool detected - excluding created_at, updated_at, approver, employee")
            
            # For payroll reports, exclude timestamps, nested breakdowns, and unnecessary IDs
            elif tool_name.lower() == 'get_payroll_salary_sheet':
                exclude_patterns.extend([
                    'created_at', 'updated_at', 'createdAt', 'updatedAt',
                    'batch_id', 'user_id', 'tenant_id',
                    'base_salary_structure_breakdown', 'grade_benefits_breakdown',
                    'fixed_addition', 'fixed_deduction', 'bonus_addition',
                    'salary_sheet', 'summary'
                ])
                logger.info("[chat_usecase] Payroll salary sheet detected - excluding timestamps, breakdowns, and IDs")
            
            report_id = self.report_service.generate(
                data=data_list,
                chat_id=chat_entry.id,
                organization_id=organization_id,
                tool_used=tool_name,
                exclude_patterns=exclude_patterns,
            )
            if report_id:
                report_url = f"/report/download/{report_id}"
            logger.info(f"[chat_usecase] Report generated | id={report_id}")
        except Exception as exc:
            logger.error(f"[chat_usecase] Step 5 failed — report generation error: {exc}")

        # 6. Ask Gemini to generate a natural language answer from the data
        logger.info("[chat_usecase] Step 6 — asking Gemini to generate natural language answer")
        try:
            if isinstance(tool_response, dict) and tool_response.get("error"):
                logger.warning(f"[chat_usecase] Tool returned error: {tool_response.get('error')}")
                answer = self.gemini.handle_out_of_scope(
                    f"The HR system returned an error: {tool_response.get('error')}. "
                    f"Original user question: {req.message}"
                )
                tool_status = "failed"
            else:
                answer = self.gemini.generate_answer(
                    user_message=req.message,
                    tool_name=tool_name,
                    data=tool_response,
                )
            logger.info(f"[chat_usecase] Gemini answer: {answer[:120]}")
        except Exception as exc:
            logger.error(f"[chat_usecase] Step 6 failed — Gemini answer generation error: {exc}")
            answer = f"Retrieved data for {tool_name} successfully."

        # 7. Save bot response
        logger.info(f"[chat_usecase] Step 7 — updating chat entry with bot response | id={chat_entry.id}")
        try:
            update_chat_response(self.db, chat_entry.id, answer)
            logger.info("[chat_usecase] Chat entry updated successfully")
        except Exception as exc:
            logger.error(f"[chat_usecase] Step 7 failed — could not save bot response: {exc}")

        response_time = f"{time.time() - start_time:.2f}s"
        logger.info(f"[chat_usecase] handle_message complete | time={response_time}")
        
        return ChatResponse(
            success=True,
            status="completed",
            data=ChatResponseData(
                chatId=chat_entry.id,
                answer=_markdown_to_plain(answer),
                answerMarkdown=answer,
                toolUsed=ToolInfo(
                    name=tool_name,
                    endpoint=f"api/{tool_name.replace('get_', '')}/{tool_name.replace('get_', '')}-list",
                    status=tool_status,
                    recordsCount=records_count if tool_status == "success" else None
                ),
                report=ReportInfo(
                    id=report_id,
                    downloadUrl=report_url,
                    format="xlsx",
                    expiresIn=300
                ) if report_url else None,
                metadata={
                    "responseTime": response_time,
                    "recordsCount": records_count,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            ),
            error=None
        )