"""
Coder Agent - Expert code generation and modification.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from aol_fire.models import Task, TaskStatus, ToolCall, FileChange
from aol_fire.core import FireConfig
from aol_fire.llm import create_chat_model
from aol_fire.agents.prompts import CODER_PROMPT


class CoderAgent:
    """
    The Coder Agent handles all code-related tasks.
    
    It can:
    - Create new files and modules
    - Modify existing code
    - Write tests
    - Fix bugs
    - Refactor code
    """
    
    def __init__(self, config: FireConfig, tools: List[Any] = None):
        self.config = config
        self.llm = create_chat_model(config, "coder")
        self.llm.system_prompt = CODER_PROMPT
        self.tools = tools or []
        self.tool_map = {t.name: t for t in self.tools}
    
    def execute_task(
        self, 
        task: Task, 
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a coding task.
        
        Args:
            task: The task to execute
            context: Additional context (file contents, etc.)
        
        Returns:
            Dictionary with results, tool calls, and file changes
        """
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        
        # Build context string
        context_str = ""
        if context:
            if "files" in context:
                files_content = "\n\n".join(
                    f"=== {path} ===\n{content[:2000]}"
                    for path, content in context["files"].items()
                )
                context_str += f"\n\nRelevant Files:\n{files_content}"
            
            if "project_info" in context:
                context_str += f"\n\nProject Info:\n{json.dumps(context['project_info'], indent=2)}"
        
        prompt = f"""Execute this coding task:

Task: {task.title}
Description: {task.description}
{context_str}

Use the available tools to:
1. Read any files you need to understand
2. Write or modify code as needed
3. Verify your changes work

Available tools: {', '.join(self.tool_map.keys())}"""
        
        messages = [HumanMessage(content=prompt)]
        
        # Build tool definitions for LLM
        tool_defs = self._get_tool_definitions()
        
        # Execute with tool calling loop
        result = {
            "success": False,
            "output": "",
            "tool_calls": [],
            "file_changes": [],
            "error": None,
        }
        
        max_iterations = 15
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get LLM response
            response = self.llm.invoke(messages, tools=tool_defs if tool_defs else None)
            
            # Check for tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                messages.append(response)
                
                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", f"call_{iteration}")
                    
                    # Execute tool
                    if tool_name in self.tool_map:
                        try:
                            tool_result = self.tool_map[tool_name].invoke(tool_args)
                            
                            # Track tool call
                            result["tool_calls"].append(ToolCall(
                                tool_name=tool_name,
                                arguments=tool_args,
                                result=str(tool_result)[:1000],
                            ))
                            
                            # Track file changes
                            if tool_name == "write_file":
                                result["file_changes"].append(FileChange(
                                    path=tool_args.get("path", "unknown"),
                                    action="created",
                                ))
                            elif tool_name == "edit_file":
                                result["file_changes"].append(FileChange(
                                    path=tool_args.get("path", "unknown"),
                                    action="modified",
                                ))
                            
                        except Exception as e:
                            tool_result = f"Error: {str(e)}"
                            result["tool_calls"].append(ToolCall(
                                tool_name=tool_name,
                                arguments=tool_args,
                                error=str(e),
                            ))
                    else:
                        tool_result = f"Unknown tool: {tool_name}"
                    
                    messages.append(ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_id
                    ))
            else:
                # No more tool calls, task complete
                result["success"] = True
                result["output"] = response.content
                break
        
        if iteration >= max_iterations:
            result["error"] = "Max iterations reached"
        
        return result
    
    def _get_tool_definitions(self) -> List[Dict]:
        """Convert tools to OpenAI function format."""
        defs = []
        for tool in self.tools:
            if hasattr(tool, 'name') and hasattr(tool, 'description'):
                schema = {}
                if hasattr(tool, 'args_schema'):
                    schema = tool.args_schema.model_json_schema()
                
                defs.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": schema,
                    }
                })
        return defs
    
    def generate_code(
        self, 
        spec: str, 
        language: str = "python",
        context: Optional[str] = None
    ) -> str:
        """
        Generate code from a specification.
        
        Args:
            spec: Description of what the code should do
            language: Programming language
            context: Additional context
        
        Returns:
            Generated code as a string
        """
        from langchain_core.messages import HumanMessage
        
        prompt = f"""Generate {language} code for the following specification:

{spec}

{f'Context: {context}' if context else ''}

Requirements:
1. Write clean, well-documented code
2. Follow {language} best practices
3. Include error handling
4. Add type hints where applicable

Respond with ONLY the code, no explanations."""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Extract code from response
        code = response.content
        
        # Try to extract from code block if present
        if "```" in code:
            parts = code.split("```")
            for part in parts[1::2]:  # Every other part (inside code blocks)
                lines = part.split("\n")
                if lines[0].strip().lower() in [language, language.lower(), ""]:
                    return "\n".join(lines[1:]).strip()
                return part.strip()
        
        return code.strip()
    
    def review_code(self, code: str, filepath: Optional[str] = None) -> Dict[str, Any]:
        """
        Review code for issues and improvements.
        
        Args:
            code: The code to review
            filepath: Optional file path for context
        
        Returns:
            Dictionary with issues and suggestions
        """
        from langchain_core.messages import HumanMessage
        
        prompt = f"""Review this code for issues and improvements:

{f'File: {filepath}' if filepath else ''}

```
{code[:5000]}
```

Provide a JSON review:
{{
    "overall_quality": "good|acceptable|needs_work|poor",
    "issues": [
        {{"severity": "critical|warning|info", "line": <number or null>, "description": "..."}}
    ],
    "suggestions": ["list", "of", "improvements"],
    "security_concerns": ["any", "security", "issues"],
    "summary": "Brief overall assessment"
}}"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        try:
            start = response.content.find('{')
            end = response.content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response.content[start:end])
        except:
            pass
        
        return {
            "overall_quality": "unknown",
            "issues": [],
            "suggestions": [],
            "security_concerns": [],
            "summary": response.content[:500],
        }
    
    def fix_error(
        self, 
        code: str, 
        error: str,
        filepath: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fix an error in code.
        
        Args:
            code: The code with the error
            error: The error message
            filepath: Optional file path
        
        Returns:
            Dictionary with fix and explanation
        """
        from langchain_core.messages import HumanMessage
        
        prompt = f"""Fix this error in the code:

{f'File: {filepath}' if filepath else ''}

Error:
{error}

Code:
```
{code[:4000]}
```

Respond with:
1. What caused the error
2. The fixed code
3. How to prevent similar errors"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Extract fixed code
        fixed_code = None
        if "```" in response.content:
            parts = response.content.split("```")
            for part in parts[1::2]:
                lines = part.split("\n")
                fixed_code = "\n".join(lines[1:] if lines[0].strip() else lines).strip()
                break
        
        return {
            "explanation": response.content,
            "fixed_code": fixed_code,
            "success": fixed_code is not None,
        }
