"""
NullForge Advanced Prompt Templates Library
State of the Art prompt engineering

Features:
- Pre-built prompts for code synthesis
- Chain-of-thought prompting
- Few-shot learning examples
- Dynamic template composition
- Prompt versioning and A/B testing
- Domain-specific templates
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class PromptCategory(Enum):
    """Categories of prompt templates."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    EXPLANATION = "explanation"
    TRANSLATION = "translation"
    PLANNING = "planning"
    AGENT = "agent"


@dataclass
class PromptTemplate:
    """A reusable prompt template."""
    id: str
    name: str
    category: PromptCategory
    template: str
    description: str = ""
    version: str = "1.0.0"
    variables: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    chain_of_thought: bool = False
    few_shot_count: int = 0
    tags: List[str] = field(default_factory=list)
    author: str = "NullForge"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = 0
    success_rate: float = 0.0
    
    def render(self, **kwargs) -> str:
        """Render the template with provided variables."""
        result = self.template
        
        # Replace variables
        for var in self.variables:
            placeholder = f"{{{var}}}"
            if var in kwargs:
                result = result.replace(placeholder, str(kwargs[var]))
            elif var.upper() in kwargs:
                result = result.replace(placeholder, str(kwargs[var.upper()]))
        
        # Add few-shot examples if requested
        if self.few_shot_count > 0 and self.examples:
            examples_text = self._format_examples(self.examples[:self.few_shot_count])
            result = examples_text + "\n\n" + result
        
        # Add chain of thought prompt if enabled
        if self.chain_of_thought:
            result += "\n\nLet's think through this step by step:"
        
        self.usage_count += 1
        return result
    
    def _format_examples(self, examples: List[Dict[str, Any]]) -> str:
        """Format few-shot examples."""
        formatted = ["Here are some examples:"]
        for i, example in enumerate(examples, 1):
            formatted.append(f"\nExample {i}:")
            if "input" in example:
                formatted.append(f"Input: {example['input']}")
            if "output" in example:
                formatted.append(f"Output: {example['output']}")
        return "\n".join(formatted)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['category'] = self.category.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        data['category'] = PromptCategory(data['category'])
        return cls(**data)


class PromptChain:
    """
    Chain multiple prompts together for complex tasks.
    
    Each step's output can be used as input for the next step.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []
    
    def add_step(
        self,
        template: PromptTemplate,
        output_key: str,
        input_mapping: Optional[Dict[str, str]] = None,
        transform: Optional[Callable] = None
    ) -> "PromptChain":
        """
        Add a step to the chain.
        
        Args:
            template: The prompt template to use
            output_key: Key to store output for next steps
            input_mapping: Map previous outputs to template variables
            transform: Optional function to transform output
        """
        self.steps.append({
            "template": template,
            "output_key": output_key,
            "input_mapping": input_mapping or {},
            "transform": transform
        })
        return self
    
    def execute(
        self,
        llm_callable: Callable,
        initial_inputs: Dict[str, Any],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Execute the prompt chain.
        
        Args:
            llm_callable: Function to call LLM
            initial_inputs: Initial inputs for first step
            verbose: Print intermediate results
            
        Returns:
            Dictionary with all outputs
        """
        context = dict(initial_inputs)
        self.results = []
        
        for i, step in enumerate(self.steps):
            template = step["template"]
            
            # Map inputs
            step_inputs = {}
            for var in template.variables:
                if var in context:
                    step_inputs[var] = context[var]
            
            # Apply custom input mapping
            for target, source in step["input_mapping"].items():
                if source in context:
                    step_inputs[target] = context[source]
            
            # Render prompt
            prompt = template.render(**step_inputs)
            
            if verbose:
                print(f"\n=== Step {i+1}: {template.name} ===")
                print(f"Prompt:\n{prompt[:500]}...")
            
            # Call LLM
            try:
                output = llm_callable(prompt)
                
                # Apply transform if provided
                if step["transform"]:
                    output = step["transform"](output)
                
                # Store result
                context[step["output_key"]] = output
                self.results.append({
                    "step": i + 1,
                    "template": template.name,
                    "output_key": step["output_key"],
                    "output": output
                })
                
                if verbose:
                    print(f"Output:\n{output[:500]}...")
                
            except Exception as e:
                self.results.append({
                    "step": i + 1,
                    "template": template.name,
                    "error": str(e)
                })
                break
        
        return context


class PromptLibrary:
    """
    Library of prompt templates with search and management.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = Path(persist_path) if persist_path else None
        self.templates: Dict[str, PromptTemplate] = {}
        
        # Load built-in templates
        self._load_builtin_templates()
        
        # Load custom templates
        if self.persist_path:
            self._load_custom_templates()
    
    def _load_builtin_templates(self):
        """Load built-in prompt templates."""
        
        # Code Generation Templates
        self.add(PromptTemplate(
            id="code_gen_basic",
            name="Basic Code Generation",
            category=PromptCategory.CODE_GENERATION,
            description="Generate code from a natural language description",
            template="""Generate {language} code for the following task:

Task: {task}

Requirements:
- Write clean, well-documented code
- Follow best practices for {language}
- Include error handling
- Add type hints where applicable

Code:""",
            variables=["language", "task"],
            tags=["basic", "generation"]
        ))
        
        self.add(PromptTemplate(
            id="code_gen_advanced",
            name="Advanced Code Generation with Planning",
            category=PromptCategory.CODE_GENERATION,
            description="Generate code with step-by-step planning",
            template="""Generate production-quality {language} code for the following task:

Task: {task}

Context:
{context}

Requirements:
{requirements}

Before writing code, analyze the task:
1. What are the main components needed?
2. What are the potential edge cases?
3. What design patterns would be appropriate?

Then write the implementation:""",
            variables=["language", "task", "context", "requirements"],
            chain_of_thought=True,
            tags=["advanced", "planning"]
        ))
        
        self.add(PromptTemplate(
            id="code_gen_api",
            name="REST API Generator",
            category=PromptCategory.CODE_GENERATION,
            description="Generate REST API endpoints",
            template="""Create a {framework} REST API with the following specifications:

Resource: {resource}
Endpoints: {endpoints}
Authentication: {auth}

Requirements:
- Proper HTTP status codes
- Request validation
- Error handling
- Documentation comments

Generate the complete API implementation:""",
            variables=["framework", "resource", "endpoints", "auth"],
            examples=[
                {
                    "input": "Create user management API",
                    "output": "from fastapi import FastAPI, HTTPException..."
                }
            ],
            few_shot_count=1,
            tags=["api", "web"]
        ))
        
        self.add(PromptTemplate(
            id="code_gen_cli",
            name="CLI Tool Generator",
            category=PromptCategory.CODE_GENERATION,
            description="Generate command-line interface tools",
            template="""Create a {language} CLI tool using {framework}:

Tool Name: {name}
Description: {description}

Commands:
{commands}

Features:
- Help documentation
- Input validation
- Colored output
- Progress indicators

Generate the complete CLI implementation:""",
            variables=["language", "framework", "name", "description", "commands"],
            tags=["cli", "tools"]
        ))
        
        # Code Review Templates
        self.add(PromptTemplate(
            id="review_comprehensive",
            name="Comprehensive Code Review",
            category=PromptCategory.CODE_REVIEW,
            description="Thorough code review with multiple aspects",
            template="""Perform a comprehensive code review of the following {language} code:

```{language}
{code}
```

Review the following aspects:

1. **Code Quality**
   - Readability and maintainability
   - Naming conventions
   - Code organization

2. **Best Practices**
   - Design patterns used
   - {language}-specific idioms
   - DRY principle adherence

3. **Performance**
   - Algorithmic efficiency
   - Memory usage
   - Potential bottlenecks

4. **Security**
   - Input validation
   - Authentication/Authorization
   - Data handling

5. **Testing**
   - Test coverage considerations
   - Edge cases

Provide specific feedback with line numbers where applicable:""",
            variables=["language", "code"],
            chain_of_thought=True,
            tags=["review", "quality"]
        ))
        
        self.add(PromptTemplate(
            id="review_quick",
            name="Quick Code Review",
            category=PromptCategory.CODE_REVIEW,
            description="Fast code review focusing on critical issues",
            template="""Quick review of this {language} code. Focus on:
- Critical bugs
- Security vulnerabilities  
- Major performance issues

Code:
```{language}
{code}
```

List only the most important issues:""",
            variables=["language", "code"],
            tags=["review", "quick"]
        ))
        
        # Debugging Templates
        self.add(PromptTemplate(
            id="debug_error",
            name="Error Debugging",
            category=PromptCategory.DEBUGGING,
            description="Debug an error message",
            template="""Debug the following error in {language}:

Error Message:
```
{error}
```

Code causing the error:
```{language}
{code}
```

Context:
{context}

Analyze:
1. What is the root cause of this error?
2. Why is it happening in this context?
3. How can it be fixed?

Provide the corrected code:""",
            variables=["language", "error", "code", "context"],
            chain_of_thought=True,
            tags=["debug", "error"]
        ))
        
        self.add(PromptTemplate(
            id="debug_logic",
            name="Logic Bug Detection",
            category=PromptCategory.DEBUGGING,
            description="Find and fix logic bugs",
            template="""The following {language} code has a logic bug:

Expected behavior: {expected}
Actual behavior: {actual}

Code:
```{language}
{code}
```

Trace through the code execution and identify:
1. Where the logic diverges from expected
2. The root cause
3. The fix

Provide corrected code:""",
            variables=["language", "expected", "actual", "code"],
            chain_of_thought=True,
            tags=["debug", "logic"]
        ))
        
        # Testing Templates
        self.add(PromptTemplate(
            id="test_unit",
            name="Unit Test Generator",
            category=PromptCategory.TESTING,
            description="Generate unit tests for code",
            template="""Generate comprehensive unit tests for this {language} code using {framework}:

Code to test:
```{language}
{code}
```

Requirements:
- Test all public functions/methods
- Include edge cases
- Test error conditions
- Use descriptive test names
- Add docstrings explaining test purpose

Generate the test file:""",
            variables=["language", "framework", "code"],
            tags=["test", "unit"]
        ))
        
        self.add(PromptTemplate(
            id="test_integration",
            name="Integration Test Generator",
            category=PromptCategory.TESTING,
            description="Generate integration tests",
            template="""Generate integration tests for this {language} {component_type}:

Component:
```{language}
{code}
```

Test scenarios:
{scenarios}

Include:
- Setup and teardown
- Mock external dependencies
- Realistic test data
- Async handling if needed

Generate the integration tests:""",
            variables=["language", "component_type", "code", "scenarios"],
            tags=["test", "integration"]
        ))
        
        # Documentation Templates
        self.add(PromptTemplate(
            id="doc_comprehensive",
            name="Comprehensive Documentation",
            category=PromptCategory.DOCUMENTATION,
            description="Generate full documentation for code",
            template="""Generate comprehensive documentation for this {language} code:

```{language}
{code}
```

Include:
1. **Overview** - High-level description
2. **Installation** - Setup instructions
3. **Usage** - How to use with examples
4. **API Reference** - All functions/classes documented
5. **Examples** - Practical usage examples
6. **Configuration** - Any configuration options
7. **Troubleshooting** - Common issues and solutions

Output in {format} format:""",
            variables=["language", "code", "format"],
            tags=["docs", "comprehensive"]
        ))
        
        self.add(PromptTemplate(
            id="doc_docstring",
            name="Docstring Generator",
            category=PromptCategory.DOCUMENTATION,
            description="Generate docstrings for functions/classes",
            template="""Generate {style} docstrings for all functions and classes in this {language} code:

```{language}
{code}
```

Include:
- Brief description
- Parameters with types
- Return values with types
- Raises/Exceptions
- Usage examples

Output the code with docstrings added:""",
            variables=["style", "language", "code"],
            tags=["docs", "docstring"]
        ))
        
        # Security Templates
        self.add(PromptTemplate(
            id="security_audit",
            name="Security Audit",
            category=PromptCategory.SECURITY,
            description="Comprehensive security audit of code",
            template="""Perform a security audit on this {language} code:

```{language}
{code}
```

Check for:
1. **Injection Vulnerabilities** - SQL, Command, XSS, etc.
2. **Authentication Issues** - Weak auth, session handling
3. **Authorization Flaws** - Missing access controls
4. **Data Exposure** - Sensitive data handling
5. **Cryptography** - Proper encryption usage
6. **Dependencies** - Known vulnerable packages
7. **Configuration** - Secure defaults
8. **Input Validation** - Proper sanitization

For each issue found:
- Severity (Critical/High/Medium/Low)
- Description
- Location
- Remediation

Security Report:""",
            variables=["language", "code"],
            chain_of_thought=True,
            tags=["security", "audit"]
        ))
        
        # Refactoring Templates
        self.add(PromptTemplate(
            id="refactor_clean",
            name="Clean Code Refactoring",
            category=PromptCategory.REFACTORING,
            description="Refactor code following clean code principles",
            template="""Refactor this {language} code following clean code principles:

```{language}
{code}
```

Apply these principles:
- Single Responsibility Principle
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple)
- Clear naming conventions
- Small, focused functions
- Proper error handling
- Remove dead code

Provide the refactored code with comments explaining changes:""",
            variables=["language", "code"],
            tags=["refactor", "clean"]
        ))
        
        self.add(PromptTemplate(
            id="refactor_performance",
            name="Performance Refactoring",
            category=PromptCategory.REFACTORING,
            description="Refactor code for better performance",
            template="""Optimize this {language} code for performance:

```{language}
{code}
```

Current issues: {issues}

Optimize for:
- Time complexity
- Space complexity
- Caching opportunities
- Lazy evaluation
- Parallelization potential

Provide optimized code with complexity analysis:""",
            variables=["language", "code", "issues"],
            tags=["refactor", "performance"]
        ))
        
        # Planning Templates
        self.add(PromptTemplate(
            id="plan_project",
            name="Project Planning",
            category=PromptCategory.PLANNING,
            description="Create a project implementation plan",
            template="""Create a detailed implementation plan for:

Project: {project}
Requirements: {requirements}
Constraints: {constraints}

Generate a plan with:
1. **Architecture Overview**
   - System design
   - Technology choices
   
2. **Task Breakdown**
   - Milestones
   - Individual tasks
   - Dependencies
   
3. **Implementation Order**
   - Critical path
   - Parallelizable tasks
   
4. **Risk Assessment**
   - Technical risks
   - Mitigation strategies
   
5. **Timeline Estimate**
   - Per task estimates
   - Total estimate

Implementation Plan:""",
            variables=["project", "requirements", "constraints"],
            chain_of_thought=True,
            tags=["planning", "project"]
        ))
        
        # Agent Templates
        self.add(PromptTemplate(
            id="agent_orchestrator",
            name="Agent Orchestrator",
            category=PromptCategory.AGENT,
            description="Orchestrate multi-step task execution",
            template="""You are an AI agent orchestrator. Your task is to break down and coordinate the execution of complex tasks.

Task: {task}
Available Tools: {tools}
Current State: {state}

Previous Steps:
{history}

Analyze the task and decide:
1. What is the next action to take?
2. Which tool to use?
3. What parameters to pass?

Output in JSON format:
{{
  "thought": "Your reasoning",
  "action": "tool_name",
  "parameters": {{}},
  "expected_outcome": "what you expect"
}}""",
            variables=["task", "tools", "state", "history"],
            tags=["agent", "orchestrator"]
        ))
        
        self.add(PromptTemplate(
            id="agent_reflection",
            name="Agent Reflection",
            category=PromptCategory.AGENT,
            description="Self-reflection for agent improvement",
            template="""Reflect on your task execution:

Task: {task}
Actions Taken: {actions}
Result: {result}
Expected: {expected}

Analyze:
1. Did you achieve the goal?
2. What went well?
3. What could be improved?
4. What would you do differently?

Reflection:""",
            variables=["task", "actions", "result", "expected"],
            chain_of_thought=True,
            tags=["agent", "reflection"]
        ))
    
    def add(self, template: PromptTemplate):
        """Add a template to the library."""
        self.templates[template.id] = template
    
    def get(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def search(
        self,
        query: Optional[str] = None,
        category: Optional[PromptCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[PromptTemplate]:
        """Search templates."""
        results = list(self.templates.values())
        
        if category:
            results = [t for t in results if t.category == category]
        
        if tags:
            results = [t for t in results if any(tag in t.tags for tag in tags)]
        
        if query:
            query_lower = query.lower()
            results = [t for t in results 
                      if query_lower in t.name.lower() 
                      or query_lower in t.description.lower()
                      or query_lower in t.template.lower()]
        
        return results
    
    def list_categories(self) -> List[PromptCategory]:
        """List all categories with templates."""
        return list(set(t.category for t in self.templates.values()))
    
    def list_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        """List templates in a category."""
        return [t for t in self.templates.values() if t.category == category]
    
    def create_chain(self, name: str, template_ids: List[str]) -> PromptChain:
        """Create a prompt chain from template IDs."""
        chain = PromptChain(name)
        for i, tid in enumerate(template_ids):
            template = self.get(tid)
            if template:
                chain.add_step(template, f"output_{i}")
        return chain
    
    def _load_custom_templates(self):
        """Load custom templates from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        for file in self.persist_path.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    template = PromptTemplate.from_dict(data)
                    self.templates[template.id] = template
            except Exception:
                pass
    
    def save_template(self, template: PromptTemplate):
        """Save a template to disk."""
        if not self.persist_path:
            return
        
        self.persist_path.mkdir(parents=True, exist_ok=True)
        file_path = self.persist_path / f"{template.id}.json"
        
        with open(file_path, "w") as f:
            json.dump(template.to_dict(), f, indent=2)
        
        self.templates[template.id] = template
    
    def export_all(self, output_path: str) -> str:
        """Export all templates to a file."""
        data = {
            "templates": [t.to_dict() for t in self.templates.values()],
            "exported_at": datetime.now().isoformat()
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return output_path


# Global library instance
_prompt_library: Optional[PromptLibrary] = None


def get_prompt_library() -> PromptLibrary:
    """Get or create the global prompt library."""
    global _prompt_library
    if _prompt_library is None:
        _prompt_library = PromptLibrary()
    return _prompt_library


def get_template(template_id: str) -> Optional[PromptTemplate]:
    """Get a template by ID."""
    return get_prompt_library().get(template_id)


def list_templates(category: Optional[PromptCategory] = None) -> List[PromptTemplate]:
    """List available templates."""
    library = get_prompt_library()
    if category:
        return library.list_by_category(category)
    return list(library.templates.values())
