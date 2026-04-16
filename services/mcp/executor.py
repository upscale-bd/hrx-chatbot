import json
from difflib import SequenceMatcher

from sqlalchemy.orm import Session
from models.tool_registry import ToolRegistry
from services.hrx.hrx_service import HRXService
from common.logger import get_logger

logger = get_logger("mcp_executor")


class MCPExecutor:
    def __init__(self, db: Session):
        logger.info("[mcp_executor] MCPExecutor initialized")
        self.db = db

    def execute_tool(self, tool_name: str, parameters: dict, organization_id: str):
        logger.info(f"[mcp_executor] execute_tool | tool_name='{tool_name}' org='{organization_id}'")
        logger.info(f"[mcp_executor] Parameters: {parameters}")

        logger.info(f"[mcp_executor] Querying DB for active tool '{tool_name}'")
        tool = self.db.query(ToolRegistry).filter_by(tool_name=tool_name, active=True).first()
        if not tool:
            logger.warning(f"[mcp_executor] Tool not found or inactive | tool_name='{tool_name}'")
            return {"error": "Tool not found"}
        logger.info(f"[mcp_executor] Tool found | endpoint='{tool.endpoint}' method='{tool.method}' inject_org={tool.inject_org}")

        input_params = parameters.copy() if parameters else {}
        body = input_params.copy()

        # If body_schema is present, only forward whitelisted keys to upstream API.
        local_filters = {}
        if tool.body_schema:
            try:
                schema = json.loads(tool.body_schema) if isinstance(tool.body_schema, str) else tool.body_schema
                allowed_keys = set(schema.keys()) if isinstance(schema, dict) else set()
                if allowed_keys:
                    # For payroll tools, include schema defaults (pagination) in body
                    # For other tools, only include user-provided allowed parameters
                    if tool_name.startswith("get_payroll"):
                        # Payroll: Start with schema defaults (page, limit) then override with user params
                        body = {k: v for k, v in schema.items()}  # Start with defaults
                        body.update({k: v for k, v in input_params.items() if k in allowed_keys})  # Override with user values
                    else:
                        # Attendance/leave/others: Keep original logic
                        body = {k: v for k, v in body.items() if k in allowed_keys}
                    
                    local_filters = {k: v for k, v in input_params.items() if k not in allowed_keys}
                    if local_filters:
                        logger.info(f"[mcp_executor] Applying local-only filters (not sent upstream): {list(local_filters.keys())}")
            except Exception as exc:
                logger.warning(f"[mcp_executor] Failed to parse body_schema for tool '{tool_name}': {exc}")

        if tool.inject_org:
            body["organizationId"] = organization_id
            logger.info("[mcp_executor] Injected organizationId into request body")

        # Handle dynamic endpoint parameters (e.g., {batch_id} in path)
        endpoint = tool.endpoint
        if "{batch_id}" in endpoint and "batch_id" in input_params:
            batch_id = input_params.pop("batch_id")
            endpoint = endpoint.replace("{batch_id}", batch_id)
            logger.info(f"[mcp_executor] Replaced {{batch_id}} in endpoint | batch_id='{batch_id}' | new_endpoint='{endpoint}'")
        elif "{batch_id}" in endpoint and "batch_id" in local_filters:
            batch_id = local_filters.pop("batch_id")
            endpoint = endpoint.replace("{batch_id}", batch_id)
            logger.info(f"[mcp_executor] Replaced {{batch_id}} from local_filters | endpoint='{endpoint}'")

        # DO NOT auto-add pagination parameters
        # Only send parameters that are explicitly provided or in the whitelist
        # If pagination is needed, it should be passed explicitly in parameters dict

        logger.info(f"[mcp_executor] Calling HRXService | endpoint='{endpoint}' method='{tool.method}'")
        response = HRXService.call(endpoint, tool.method, body)
        logger.info(f"[mcp_executor] HRXService response type={type(response).__name__}")
        
        # Apply local client-side filters to the response
        if isinstance(response, list) and local_filters:
            before_count = len(response)
            original_response = response.copy() if response else []  # Keep original for debug
            
            # NOTE: For get_payroll_batches, skip name filtering (batches don't have employee names)
            # Name filtering is for salary sheets only (app-side auto-chaining will handle it)
            skip_name_filter = tool_name == "get_payroll_batches"
            
            # Filter by name (with case-insensitive substring match)
            # SKIP for batch queries — name filtering happens at salary-sheet level
            if not skip_name_filter and "name" in local_filters and isinstance(local_filters["name"], str):
                name_q = local_filters["name"].strip().lower()
                if name_q:
                    fuzzy_hits = 0
                    before_name = len(response)
                    response = [
                        row for row in response
                        if isinstance(row, dict) and (
                            self._row_name_matches(row, name_q)
                        )
                    ]
                    for row in response:
                        match_info = self._row_name_match_info(row, name_q)
                        if match_info.get("fuzzy"):
                            fuzzy_hits += 1
                    logger.info(f"[mcp_executor] Local name filter applied | query='{name_q}' | before={before_name} after={len(response)}")
                    if fuzzy_hits:
                        logger.info(f"[mcp_executor] Local name filter fuzzy matches used | count={fuzzy_hits}")
                    # Debug: if 0 results, show what fields are available in first record
                    if len(response) == 0 and before_name > 0 and original_response:
                        first_record = original_response[0] if isinstance(original_response[0], dict) else {}
                        logger.warning(f"[mcp_executor] Name filter found NO matches for '{name_q}' | Sample attendance record keys: {list(first_record.keys())}")
            elif skip_name_filter and "name" in local_filters:
                logger.info(f"[mcp_executor] ⏭️  Skipping name filter for payroll batches (name will be used in auto-chaining for salary sheet)")
            
            # Filter by employee_id
            if "employee_id" in local_filters and local_filters["employee_id"]:
                emp_id = str(local_filters["employee_id"]).strip().lower()
                if emp_id:
                    before_emp = len(response)
                    response = [
                        row for row in response
                        if isinstance(row, dict) and (
                            # Check top-level employee_id
                            str(row.get("employee_id", "")).lower() == emp_id
                            # Check nested employee.employee_id (for leave/attendance records)
                            or (isinstance(row.get("employee"), dict) and str(row.get("employee", {}).get("employee_id", "")).lower() == emp_id)
                        )
                    ]
                    logger.info(f"[mcp_executor] Local employee_id filter applied | id='{emp_id}' | before={before_emp} after={len(response)}")
            
            # Filter by leaveType (check both camelCase and snake_case)
            if "leaveType" in local_filters and isinstance(local_filters["leaveType"], str):
                leave_type = local_filters["leaveType"].strip().lower()
                if leave_type:
                    before_type = len(response)
                    response = [
                        row for row in response
                        if isinstance(row, dict) and (
                            leave_type in str(row.get("leaveType", "")).lower()
                            or leave_type in str(row.get("leave_type", "")).lower()
                        )
                    ]
                    logger.info(f"[mcp_executor] Local leaveType filter applied | type='{leave_type}' | before={before_type} after={len(response)}")
            
            # Filter by status (checks both 'status' for leaves and 'checkInStatus' for attendance)
            if "status" in local_filters and isinstance(local_filters["status"], str):
                status_q = local_filters["status"].strip().lower()
                if status_q:
                    before_status = len(response)
                    response = [
                        row for row in response
                        if isinstance(row, dict)
                        and (
                            status_q in str(row.get("status", "")).lower()
                            or status_q in str(row.get("checkInStatus", "")).lower()
                        )
                    ]
                    logger.info(f"[mcp_executor] Local status filter applied | status='{status_q}' | before={before_status} after={len(response)}")
            
            # Filter by checkInStatus (for attendance records - late, on time, absent, etc.)
            if "checkInStatus" in local_filters and isinstance(local_filters["checkInStatus"], str):
                check_status = local_filters["checkInStatus"].strip().lower()
                if check_status:
                    before_check = len(response)
                    response = [
                        row for row in response
                        if isinstance(row, dict)
                        and check_status in str(row.get("checkInStatus", "")).lower()
                    ]
                    logger.info(f"[mcp_executor] Local checkInStatus filter applied | status='{check_status}' | before={before_check} after={len(response)}")
            
            # Filter by checkInTime (time comparison - e.g., "9:00", "09:00", "9", "9am")
            if "checkInTime" in local_filters and isinstance(local_filters["checkInTime"], str):
                check_in_time_q = local_filters["checkInTime"].strip().lower()
                if check_in_time_q:
                    before_time = len(response)
                    response = self._filter_by_time(response, check_in_time_q, "checkInTime", logger)
                    logger.info(f"[mcp_executor] Local checkInTime filter applied | time='{check_in_time_q}' | before={before_time} after={len(response)}")
            
            # Filter by checkOutTime (time comparison - e.g., "17:00", "5pm", "5")
            if "checkOutTime" in local_filters and isinstance(local_filters["checkOutTime"], str):
                check_out_time_q = local_filters["checkOutTime"].strip().lower()
                if check_out_time_q:
                    before_time = len(response)
                    response = self._filter_by_time(response, check_out_time_q, "checkOutTime", logger)
                    logger.info(f"[mcp_executor] Local checkOutTime filter applied | time='{check_out_time_q}' | before={before_time} after={len(response)}")
            
            # Filter by month (handles "2026-03", "03", "3", "March", etc.)
            if "month" in local_filters and local_filters["month"]:
                month_q = str(local_filters["month"]).strip().lower()
                if month_q:
                    before_month = len(response)
                    response = self._filter_by_month(response, month_q, logger)
                    logger.info(f"[mcp_executor] Local month filter applied | month='{month_q}' | before={before_month} after={len(response)}")
            
            # Filter by year (handles "2026", "26", etc.)
            if "year" in local_filters and local_filters["year"]:
                year_q = str(local_filters["year"]).strip().lower()
                if year_q:
                    before_year = len(response)
                    response = self._filter_by_year(response, year_q, logger)
                    logger.info(f"[mcp_executor] Local year filter applied | year='{year_q}' | before={before_year} after={len(response)}")
            
            if len(response) < before_count:
                logger.info(f"[mcp_executor] Local filters reduced results | total_applied_filters={len([f for f in local_filters if local_filters[f]])}")

        if isinstance(response, dict) and response.get("error"):
            logger.warning(f"[mcp_executor] HRXService returned error: {response.get('error')}")
        elif isinstance(response, list):
            logger.info(f"[mcp_executor] HRXService returned {len(response)} record(s)")
            # Post-process response to format for better LLM understanding
            response = self._format_response_for_llm(response, tool_name, local_filters)
        
        return response

    def _extract_candidate_names(self, row: dict) -> list:
        """Extract possible employee name strings from top-level and nested fields."""
        candidates = []
        
        # Try direct top-level name fields first
        direct_keys = (
            "name", "fullName", "full_name", "employeeName", "employee_name",
            "firstName", "first_name", "lastName", "last_name",
            "empName", "emp_name", "employeeFullName", "employee_full_name"
        )

        for key in direct_keys:
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append(value.strip())

        # Try nested objects
        nested_objects = (
            row.get("employee"),
            row.get("employee_info"),
            row.get("staff"),
            row.get("user"),
            row.get("attendee"),
            row.get("emp"),
        )
        for obj in nested_objects:
            if isinstance(obj, dict):
                for key in direct_keys:
                    value = obj.get(key)
                    if isinstance(value, str) and value.strip():
                        candidates.append(value.strip())

        # Build full name from first/last if present
        first = row.get("firstName") or row.get("first_name") or row.get("first") or row.get("fname")
        last = row.get("lastName") or row.get("last_name") or row.get("last") or row.get("lname")
        if isinstance(first, str) and isinstance(last, str) and (first.strip() or last.strip()):
            full = f"{first.strip()} {last.strip()}".strip()
            if full:
                candidates.append(full)

        # Deduplicate while preserving order
        deduped = []
        seen = set()
        for name in candidates:
            norm = name.lower()
            if norm not in seen:
                seen.add(norm)
                deduped.append(name)
        
        return deduped

    def _row_name_match_info(self, row: dict, name_q: str) -> dict:
        """Return match metadata for a row against query name."""
        candidates = self._extract_candidate_names(row)
        if not candidates:
            return {"matched": False, "fuzzy": False, "best": "", "score": 0.0}

        # Exact/substring pass first
        for candidate in candidates:
            c = candidate.lower()
            if name_q in c or c in name_q:
                return {"matched": True, "fuzzy": False, "best": candidate, "score": 1.0}

        # Fuzzy fallback
        best_score = 0.0
        best_name = ""
        for candidate in candidates:
            score = SequenceMatcher(None, name_q, candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_name = candidate

        # 0.72 allows common transliteration/typo variance
        if best_score >= 0.72:
            return {"matched": True, "fuzzy": True, "best": best_name, "score": best_score}

        return {"matched": False, "fuzzy": False, "best": best_name, "score": best_score}

    def _row_name_matches(self, row: dict, name_q: str) -> bool:
        return self._row_name_match_info(row, name_q).get("matched", False)

    def _format_response_for_llm(self, data: list, tool_name: str, filters: dict) -> list:
        """Format response data to make it clearer for LLM processing.
        Extracts employee names, aggregates info, and adds summary fields."""
        if not data or not isinstance(data, list):
            return data
        
        try:
            # For leave-related queries, enhance with employee info
            if tool_name == "get_leave":
                formatted = []
                for item in data:
                    if isinstance(item, dict):
                        # Extract employee info from nested structure
                        emp_info = item.get("employee", {})
                        emp_name = emp_info.get("name", "Unknown")
                        emp_id = emp_info.get("employee_id", "")
                        
                        # Add flattened fields for easier LLM understanding
                        enhanced = item.copy()
                        enhanced["employee_name"] = emp_name
                        enhanced["employee_id"] = emp_id
                        enhanced["applying_for"] = f"{emp_name} (ID: {emp_id})" if emp_id else emp_name
                        
                        # Parse dates for clarity
                        start = item.get("start_date", "")
                        end = item.get("end_date", "")
                        num_days = item.get("num_days", "")
                        leave_type = item.get("leave_type", "")
                        status = item.get("status", "")
                        
                        enhanced["date_range"] = f"{start} to {end}"
                        enhanced["summary"] = f"{emp_name} took {num_days} days of {leave_type} leave ({status})"
                        
                        formatted.append(enhanced)
                
                logger.info(f"[mcp_executor] Formatted {len(formatted)} leave records for LLM | added employee_name and summary fields")
                return formatted
            
            # For attendance-related queries
            elif tool_name == "get_attendance":
                formatted = []
                for item in data:
                    if isinstance(item, dict):
                        # Extract employee info
                        emp_info = item.get("employee", {})
                        emp_name = emp_info.get("name", "Unknown")
                        emp_id = emp_info.get("employee_id", "")
                        
                        enhanced = item.copy()
                        enhanced["employee_name"] = emp_name
                        enhanced["employee_id"] = emp_id
                        
                        # Add summary
                        date = item.get("date", "")
                        status = item.get("status", "")
                        enhanced["summary"] = f"{emp_name} was {status} on {date}"
                        
                        formatted.append(enhanced)
                
                logger.info(f"[mcp_executor] Formatted {len(formatted)} attendance records for LLM")
                return formatted
            
            # For payroll salary sheet queries
            elif tool_name == "get_payroll_salary_sheet":
                formatted = []
                for item in data:
                    if isinstance(item, dict):
                        enhanced = item.copy()
                        emp_name = item.get("employee_name", "Unknown")
                        emp_id = item.get("employee_id", "N/A")
                        net_salary = item.get("net_salary", "0")
                        
                        # Add summary
                        enhanced["summary"] = f"{emp_name} (ID: {emp_id}) - Net Salary: {net_salary}"
                        
                        formatted.append(enhanced)
                
                logger.info(f"[mcp_executor] Formatted {len(formatted)} payroll salary sheet records for LLM")
                return formatted
            
            # For other tools, return as-is
            return data
        
        except Exception as exc:
            logger.warning(f"[mcp_executor] Error formatting response for LLM: {exc}")
            return data
    
    def _filter_by_time(self, data: list, time_query: str, field_name: str, logger) -> list:
        """Filter by time comparison. Supports formats like:
        - "9" or "9:00" -> after 09:00
        - "after 9" -> after 09:00
        - "before 5" -> before 17:00
        - "17:30" -> after 17:30
        - "9am" -> after 09:00
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
            logger.warning(f"[mcp_executor] Could not parse time '{time_query}' for {field_name}")
            return data
        
        target_time = f"{hour:02d}:{minute:02d}"
        logger.debug(f"[mcp_executor] _filter_by_time: field={field_name}, comparison={comparison}, target_time={target_time}")
        
        filtered = []
        for row in data:
            if not isinstance(row, dict):
                filtered.append(row)
                continue
            
            time_str = str(row.get(field_name, "")).strip()
            if not time_str:
                continue
            
            # Extract time from ISO format: "2026-02-10T16:30:03.550Z" -> "16:30"
            if "T" in time_str:
                time_part = time_str.split("T")[1]  # "16:30:03.550Z"
                time_part = time_part.split(".")[0]  # "16:30:03"
                time_part = time_part[:5]  # "16:30"
            else:
                time_part = time_str[:5]  # First 5 chars
            
            try:
                if comparison == "after":
                    if time_part >= target_time:
                        filtered.append(row)
                else:  # before
                    if time_part <= target_time:
                        filtered.append(row)
            except Exception as e:
                logger.debug(f"[mcp_executor] Time comparison error: {e}")
                filtered.append(row)  # Include on error
        
        return filtered
    
    def _filter_by_month(self, data: list, month_query: str, logger) -> list:
        """Filter records by month. Extracts from date fields. Handles formats: "2026-03", "03", "3", "March"."""
        month_map = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        
        # Extract month number from query (handle "2026-03", "03", "3", "march")
        month_num = None
        if "-" in month_query:  # "2026-03" format
            parts = month_query.split("-", 1)
            if len(parts) == 2:
                month_num = parts[1].lstrip("0") or "0"
        elif month_query.isdigit():  # "03" or "3" format
            month_num = month_query.lstrip("0") or "0"
        else:  # Month name like "march"
            month_num = month_map.get(month_query.lower(), None)
        
        if not month_num:
            logger.warning(f"[mcp_executor] Could not parse month from query: {month_query}")
            return data
        
        logger.debug(f"[mcp_executor] month_filter: normalized month={month_num}")
        
        filtered = []
        for row in data:
            if not isinstance(row, dict):
                continue
            
            found_match = False
            
            # Try direct month field first
            for field_name in ["month", "Month"]:
                record_month = str(row.get(field_name, "")).strip().lstrip("0") or "0"
                if record_month == month_num:
                    filtered.append(row)
                    found_match = True
                    break
            
            if found_match:
                continue
            
            # Extract month from ISO date fields (e.g., "2026-02-15T00:00:00.000Z")
            for date_field in ["start_date", "date", "end_date", "applied_at"]:
                date_str = str(row.get(date_field, "")).strip()
                if date_str and len(date_str) >= 7:  # At least "2026-02"
                    try:
                        # Extract YYYY-MM from ISO format
                        date_part = date_str[:7]  # "2026-02"
                        record_month = date_part.split("-")[1].lstrip("0") or "0"
                        if record_month == month_num:
                            filtered.append(row)
                            found_match = True
                            break
                    except Exception as e:
                        logger.debug(f"[mcp_executor] Error parsing date {date_field}={date_str}: {e}")
            
        
        return filtered
    
    def _filter_by_year(self, data: list, year_query: str, logger) -> list:
        """Filter records by year. Extracts from date fields. Handles formats: "2026", "26"."""
        # Normalize year (handle "2026" or "26")
        year_query = year_query.strip()
        
        # If 2-digit year, expand to 4-digit
        if year_query.isdigit() and len(year_query) == 2:
            # Assume 00-30 -> 2000-2030, 31-99 -> 1931-1999
            y = int(year_query)
            year_num = str(2000 + y) if y <= 30 else str(1900 + y)
        elif year_query.isdigit() and len(year_query) == 4:
            year_num = year_query
        else:
            logger.warning(f"[mcp_executor] Could not parse year from query: {year_query}")
            return data
        
        logger.debug(f"[mcp_executor] year_filter: normalized year={year_num}")
        
        filtered = []
        for row in data:
            if not isinstance(row, dict):
                continue
            
            found_match = False
            
            # Try direct year field first
            for field_name in ["year", "Year"]:
                record_year = str(row.get(field_name, "")).strip()
                if record_year == year_num:
                    filtered.append(row)
                    found_match = True
                    break
            
            if found_match:
                continue
            
            # Extract year from ISO date fields (e.g., "2026-02-15T00:00:00.000Z")
            for date_field in ["start_date", "date", "end_date", "applied_at"]:
                date_str = str(row.get(date_field, "")).strip()
                if date_str and len(date_str) >= 4:  # At least "2026"
                    try:
                        # Extract YYYY from ISO format
                        record_year = date_str[:4]
                        if record_year == year_num:
                            filtered.append(row)
                            found_match = True
                            break
                    except Exception as e:
                        logger.debug(f"[mcp_executor] Error parsing date {date_field}={date_str}: {e}")
        
        return filtered