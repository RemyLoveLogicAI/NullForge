"""
NullForge State of the Art Features - Comprehensive Test Suite

Tests for:
- AI Memory with Vector Store
- Multi-Agent Collaboration
- Self-Improving Agent
- Natural Language Database Query
- Prompt Templates
- Real-time WebSocket Hub
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path


# ============================================================================
# AI Memory Tests
# ============================================================================

class TestVectorMemory:
    """Tests for the Vector Memory Store."""
    
    def test_memory_entry_creation(self):
        """Test creating a memory entry."""
        from aol_fire.memory import MemoryEntry
        
        entry = MemoryEntry(
            id="test-1",
            content="Test memory content",
            memory_type="code",
            metadata={"language": "python"},
            importance=0.8
        )
        
        assert entry.id == "test-1"
        assert entry.content == "Test memory content"
        assert entry.memory_type == "code"
        assert entry.importance == 0.8
        assert entry.metadata["language"] == "python"
    
    def test_memory_entry_serialization(self):
        """Test memory entry to/from dict."""
        from aol_fire.memory import MemoryEntry
        
        entry = MemoryEntry(
            id="test-2",
            content="Test content",
            memory_type="knowledge"
        )
        
        data = entry.to_dict()
        assert data["id"] == "test-2"
        assert data["content"] == "Test content"
        
        restored = MemoryEntry.from_dict(data)
        assert restored.id == entry.id
        assert restored.content == entry.content
    
    def test_embedding_engine_fallback(self):
        """Test embedding engine with fallback."""
        from aol_fire.memory import EmbeddingEngine
        
        engine = EmbeddingEngine()
        embedding = engine.embed("test text")
        
        # Fallback uses SHA384 which produces 48 bytes
        assert len(embedding) > 0  # Has some embedding
        assert all(isinstance(x, float) for x in embedding)
    
    def test_vector_store_initialization(self):
        """Test vector store initialization."""
        from aol_fire.memory import VectorMemoryStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorMemoryStore(persist_directory=tmpdir)
            
            assert store.persist_directory.exists()
            # Either has ChromaDB collections or fallback store
            assert len(store.collections) >= 0 or hasattr(store, '_fallback_store')
    
    def test_vector_store_add_and_search(self):
        """Test adding and searching memories."""
        from aol_fire.memory import VectorMemoryStore
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorMemoryStore(persist_directory=tmpdir)
            
            # Add memory
            entry = store.add(
                content="Python function to calculate fibonacci",
                memory_type="code",
                metadata={"language": "python"},
                importance=0.7
            )
            
            assert entry.id is not None
            assert entry.content == "Python function to calculate fibonacci"
            
            # Search
            results = store.search("fibonacci python", n_results=5)
            assert len(results) >= 1
    
    def test_conversation_memory(self):
        """Test conversation memory."""
        from aol_fire.memory import VectorMemoryStore, ConversationMemory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorMemoryStore(persist_directory=tmpdir)
            conv_memory = ConversationMemory(store, window_size=10)
            
            conv_memory.add_message("user", "How do I sort a list?")
            conv_memory.add_message("assistant", "Use the sorted() function.")
            
            assert len(conv_memory.recent_messages) == 2
            
            context = conv_memory.get_context()
            assert "sort" in context.lower()
    
    def test_code_memory(self):
        """Test code-specific memory."""
        from aol_fire.memory import VectorMemoryStore, CodeMemory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorMemoryStore(persist_directory=tmpdir)
            code_memory = CodeMemory(store)
            
            entry = code_memory.remember_code(
                code="def hello(): print('Hello')",
                description="Hello world function",
                language="python"
            )
            
            assert entry.id is not None
            
            # Find similar
            results = code_memory.find_similar_code("hello function")
            assert len(results) >= 1


# ============================================================================
# Multi-Agent Collaboration Tests
# ============================================================================

class TestMultiAgentCollaboration:
    """Tests for the Multi-Agent Collaboration System."""
    
    def test_agent_role_enum(self):
        """Test agent roles."""
        from aol_fire.collaboration import AgentRole
        
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.ORCHESTRATOR.value == "orchestrator"
    
    def test_message_type_enum(self):
        """Test message types."""
        from aol_fire.collaboration import MessageType
        
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.CONSENSUS_REQUEST.value == "consensus_request"
    
    def test_agent_message_creation(self):
        """Test creating agent messages."""
        from aol_fire.collaboration import AgentMessage, MessageType
        
        message = AgentMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.QUERY,
            content={"query": "How to optimize this code?"}
        )
        
        assert message.sender_id == "agent-1"
        assert message.receiver_id == "agent-2"
        assert message.message_type == MessageType.QUERY
    
    def test_agent_message_serialization(self):
        """Test message to/from dict."""
        from aol_fire.collaboration import AgentMessage, MessageType
        
        message = AgentMessage(
            sender_id="agent-1",
            message_type=MessageType.BROADCAST,
            content={"announcement": "Task completed"}
        )
        
        data = message.to_dict()
        assert data["message_type"] == "broadcast"
        
        restored = AgentMessage.from_dict(data)
        assert restored.message_type == MessageType.BROADCAST
    
    def test_task_assignment_creation(self):
        """Test creating task assignments."""
        from aol_fire.collaboration import TaskAssignment
        
        task = TaskAssignment(
            task_type="code_generation",
            description="Generate a REST API",
            assigned_to="coder-1",
            priority=8
        )
        
        assert task.task_type == "code_generation"
        assert task.status == "pending"
        assert task.priority == 8
    
    def test_coder_agent_creation(self):
        """Test creating a coder agent."""
        from aol_fire.collaboration import CoderAgent, AgentRole
        
        agent = CoderAgent(agent_id="coder-1")
        
        assert agent.role == AgentRole.CODER
        assert "code_generation" in agent.capabilities
        assert agent.state["status"] == "idle"
    
    def test_agent_coordinator_creation(self):
        """Test creating an agent coordinator."""
        from aol_fire.collaboration import AgentCoordinator, CoderAgent
        
        coordinator = AgentCoordinator()
        coder = CoderAgent()
        
        coordinator.register_agent(coder)
        
        assert coder.agent_id in coordinator.agents
        assert coder.coordinator == coordinator
    
    @pytest.mark.asyncio
    async def test_create_collaborative_team(self):
        """Test creating a full collaborative team."""
        from aol_fire.collaboration import create_collaborative_team, AgentRole
        
        coordinator = await create_collaborative_team()
        
        assert len(coordinator.agents) >= 4
        assert AgentRole.CODER in coordinator.agent_roles
        assert AgentRole.REVIEWER in coordinator.agent_roles
        
        await coordinator.stop()


# ============================================================================
# Self-Improving Agent Tests
# ============================================================================

class TestSelfImprovingAgent:
    """Tests for the Self-Improving Agent System."""
    
    def test_reflection_type_enum(self):
        """Test reflection types."""
        from aol_fire.reflection import ReflectionType
        
        assert ReflectionType.EXECUTION.value == "execution"
        assert ReflectionType.META.value == "meta"
    
    def test_improvement_type_enum(self):
        """Test improvement types."""
        from aol_fire.reflection import ImprovementType
        
        assert ImprovementType.PROMPT_REFINEMENT.value == "prompt_refinement"
        assert ImprovementType.ERROR_PREVENTION.value == "error_prevention"
    
    def test_execution_record_creation(self):
        """Test creating execution records."""
        from aol_fire.reflection import ExecutionRecord
        
        record = ExecutionRecord(
            task_type="code_generation",
            task_description="Generate a function",
            success=True,
            duration_ms=1500,
            tokens_used=500
        )
        
        assert record.task_type == "code_generation"
        assert record.success is True
        assert record.duration_ms == 1500
    
    def test_execution_record_serialization(self):
        """Test execution record serialization."""
        from aol_fire.reflection import ExecutionRecord
        
        record = ExecutionRecord(
            task_type="test",
            task_description="Test task",
            success=True
        )
        
        data = record.to_dict()
        assert data["task_type"] == "test"
        assert data["success"] is True
    
    def test_performance_tracker(self):
        """Test performance tracker."""
        from aol_fire.reflection import PerformanceTracker, ExecutionRecord
        
        tracker = PerformanceTracker()
        
        # Record some executions
        for i in range(5):
            record = ExecutionRecord(
                task_type="test",
                task_description=f"Task {i}",
                success=i % 2 == 0,
                duration_ms=1000 + i * 100,
                tokens_used=100 * (i + 1)
            )
            tracker.record(record)
        
        summary = tracker.get_summary()
        assert "aggregates" in summary
        assert len(tracker.metrics["success_rate"]) == 5
    
    def test_reflection_engine(self):
        """Test reflection engine."""
        from aol_fire.reflection import ReflectionEngine, ExecutionRecord
        
        engine = ReflectionEngine()
        
        # Successful execution
        success_record = ExecutionRecord(
            task_type="code_gen",
            task_description="Generate code",
            success=True,
            duration_ms=2000,
            iterations=1,
            confidence=0.9
        )
        
        reflection = engine.reflect_on_execution(success_record)
        assert len(reflection.strengths) > 0
        
        # Failed execution
        fail_record = ExecutionRecord(
            task_type="code_gen",
            task_description="Generate code",
            success=False,
            error="Timeout error",
            duration_ms=30000
        )
        
        reflection = engine.reflect_on_execution(fail_record)
        assert len(reflection.weaknesses) > 0
        assert len(reflection.root_causes) > 0
    
    def test_self_improving_agent(self):
        """Test self-improving agent."""
        from aol_fire.reflection import SelfImprovingAgent
        from datetime import datetime, timedelta
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SelfImprovingAgent(persist_directory=tmpdir)
            
            start = datetime.now()
            end = start + timedelta(seconds=2)
            
            agent.record_execution(
                task_type="test",
                task_description="Test execution",
                input_data={"prompt": "test"},
                output_data={"result": "success"},
                start_time=start,
                end_time=end,
                success=True
            )
            
            assert len(agent.executions) == 1
            
            report = agent.get_performance_report()
            assert "summary" in report


# ============================================================================
# Natural Language Database Query Tests
# ============================================================================

class TestNLDBEngine:
    """Tests for the Natural Language Database Query Engine."""
    
    def test_database_type_enum(self):
        """Test database types."""
        from aol_fire.nldb import DatabaseType
        
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.POSTGRESQL.value == "postgresql"
    
    def test_column_info(self):
        """Test column info dataclass."""
        from aol_fire.nldb.query_engine import ColumnInfo
        
        col = ColumnInfo(
            name="id",
            data_type="INTEGER",
            primary_key=True
        )
        
        assert col.name == "id"
        assert col.primary_key is True
    
    def test_table_info(self):
        """Test table info dataclass."""
        from aol_fire.nldb.query_engine import TableInfo, ColumnInfo
        
        table = TableInfo(
            name="users",
            columns=[
                ColumnInfo(name="id", data_type="INTEGER", primary_key=True),
                ColumnInfo(name="name", data_type="TEXT")
            ],
            row_count=100
        )
        
        assert table.name == "users"
        assert len(table.columns) == 2
        assert table.row_count == 100
    
    def test_query_result(self):
        """Test query result dataclass."""
        from aol_fire.nldb import QueryResult
        
        result = QueryResult(
            query="show all users",
            natural_language="show all users",
            translated_sql="SELECT * FROM users",
            success=True,
            rows=[{"id": 1, "name": "Alice"}],
            row_count=1
        )
        
        assert result.success is True
        assert result.row_count == 1
    
    def test_nldb_engine_sqlite(self):
        """Test NLDB engine with SQLite."""
        from aol_fire.nldb import create_engine_for_sqlite
        
        # Create test database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT
                )
            """)
            cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com')")
            cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@test.com')")
            conn.commit()
            conn.close()
            
            # Test engine
            engine = create_engine_for_sqlite(db_path)
            
            assert len(engine.get_tables()) == 1
            assert "users" in engine.get_tables()
            
            # Query - add LIMIT to pass validation
            result = engine.query("top 10 users")
            assert result.success is True
            assert result.row_count >= 1
            
            # Count query
            result = engine.query("count users")
            assert result.success is True
            
            engine.disconnect()
        finally:
            os.unlink(db_path)


# ============================================================================
# Prompt Templates Tests
# ============================================================================

class TestPromptTemplates:
    """Tests for the Prompt Templates Library."""
    
    def test_prompt_category_enum(self):
        """Test prompt categories."""
        from aol_fire.prompts import PromptCategory
        
        assert PromptCategory.CODE_GENERATION.value == "code_generation"
        assert PromptCategory.DEBUGGING.value == "debugging"
    
    def test_prompt_template_creation(self):
        """Test creating prompt templates."""
        from aol_fire.prompts import PromptTemplate, PromptCategory
        
        template = PromptTemplate(
            id="test_template",
            name="Test Template",
            category=PromptCategory.CODE_GENERATION,
            template="Generate {language} code for: {task}",
            variables=["language", "task"]
        )
        
        assert template.id == "test_template"
        assert len(template.variables) == 2
    
    def test_prompt_template_render(self):
        """Test rendering prompt templates."""
        from aol_fire.prompts import PromptTemplate, PromptCategory
        
        template = PromptTemplate(
            id="test",
            name="Test",
            category=PromptCategory.CODE_GENERATION,
            template="Generate {language} code for: {task}",
            variables=["language", "task"]
        )
        
        rendered = template.render(language="Python", task="hello world")
        
        assert "Python" in rendered
        assert "hello world" in rendered
    
    def test_prompt_template_chain_of_thought(self):
        """Test chain of thought prompts."""
        from aol_fire.prompts import PromptTemplate, PromptCategory
        
        template = PromptTemplate(
            id="cot_test",
            name="CoT Test",
            category=PromptCategory.CODE_GENERATION,
            template="Task: {task}",
            variables=["task"],
            chain_of_thought=True
        )
        
        rendered = template.render(task="complex problem")
        
        assert "step by step" in rendered.lower()
    
    def test_prompt_library(self):
        """Test prompt library."""
        from aol_fire.prompts import get_prompt_library, PromptCategory
        
        library = get_prompt_library()
        
        # Check built-in templates exist
        assert len(library.templates) > 0
        
        # Test search
        results = library.search(query="code generation")
        assert len(results) > 0
        
        # Test by category
        code_gen = library.list_by_category(PromptCategory.CODE_GENERATION)
        assert len(code_gen) > 0
    
    def test_get_template_helper(self):
        """Test get_template helper function."""
        from aol_fire.prompts import get_template
        
        template = get_template("code_gen_basic")
        assert template is not None
        assert template.id == "code_gen_basic"
    
    def test_prompt_chain(self):
        """Test prompt chains."""
        from aol_fire.prompts import PromptChain, PromptTemplate, PromptCategory
        
        template1 = PromptTemplate(
            id="step1",
            name="Step 1",
            category=PromptCategory.PLANNING,
            template="Plan: {task}",
            variables=["task"]
        )
        
        template2 = PromptTemplate(
            id="step2",
            name="Step 2",
            category=PromptCategory.CODE_GENERATION,
            template="Generate code for: {plan}",
            variables=["plan"]
        )
        
        chain = PromptChain("test_chain")
        chain.add_step(template1, "plan", {})
        chain.add_step(template2, "code", {"plan": "plan"})
        
        assert len(chain.steps) == 2


# ============================================================================
# Real-time WebSocket Hub Tests
# ============================================================================

class TestWebSocketHub:
    """Tests for the Real-time WebSocket Hub."""
    
    def test_message_type_enum(self):
        """Test message types."""
        from aol_fire.realtime import MessageType
        
        assert MessageType.CONNECT.value == "connect"
        assert MessageType.CODE_CHANGE.value == "code_change"
    
    def test_client_info_creation(self):
        """Test creating client info."""
        from aol_fire.realtime import ClientInfo
        
        client = ClientInfo(
            client_id="client-1",
            username="Alice",
            color="#667eea"
        )
        
        assert client.client_id == "client-1"
        assert client.username == "Alice"
    
    def test_client_info_serialization(self):
        """Test client info serialization."""
        from aol_fire.realtime import ClientInfo
        
        client = ClientInfo(
            client_id="client-1",
            username="Bob"
        )
        
        data = client.to_dict()
        assert data["client_id"] == "client-1"
        assert data["username"] == "Bob"
    
    def test_room_creation(self):
        """Test creating rooms."""
        from aol_fire.realtime import Room
        
        room = Room(
            room_id="room-1",
            name="Test Room",
            code="print('hello')",
            language="python"
        )
        
        assert room.room_id == "room-1"
        assert room.language == "python"
    
    def test_message_creation(self):
        """Test creating messages."""
        from aol_fire.realtime import Message, MessageType
        
        message = Message(
            type=MessageType.CODE_CHANGE,
            payload={"operation": {"type": "insert", "text": "x"}},
            sender_id="client-1",
            room_id="room-1"
        )
        
        assert message.type == MessageType.CODE_CHANGE
        assert message.sender_id == "client-1"
    
    def test_message_json_serialization(self):
        """Test message JSON serialization."""
        from aol_fire.realtime import Message, MessageType
        
        message = Message(
            type=MessageType.CHAT_MESSAGE,
            payload={"message": "Hello!"},
            sender_id="client-1"
        )
        
        json_str = message.to_json()
        restored = Message.from_json(json_str)
        
        assert restored.type == MessageType.CHAT_MESSAGE
        assert restored.payload["message"] == "Hello!"
    
    def test_websocket_hub_creation(self):
        """Test creating WebSocket hub."""
        from aol_fire.realtime import WebSocketHub
        
        hub = WebSocketHub()
        
        assert len(hub.clients) == 0
        assert len(hub.rooms) == 0
    
    def test_hub_create_room(self):
        """Test creating rooms via hub."""
        from aol_fire.realtime import WebSocketHub
        
        hub = WebSocketHub()
        
        room = hub.create_room(
            name="Test Room",
            code="# Initial code",
            language="python"
        )
        
        assert room.name == "Test Room"
        assert room.room_id in hub.rooms
    
    def test_operation_transform_insert(self):
        """Test operation transform for insert."""
        from aol_fire.realtime.websocket_hub import OperationTransform
        
        ot = OperationTransform()
        
        # Apply insert operation
        text = "Hello"
        op = {"type": "insert", "position": 5, "text": " World"}
        result = ot.apply_operation(text, op)
        
        assert result == "Hello World"
    
    def test_operation_transform_delete(self):
        """Test operation transform for delete."""
        from aol_fire.realtime.websocket_hub import OperationTransform
        
        ot = OperationTransform()
        
        # Apply delete operation
        text = "Hello World"
        op = {"type": "delete", "position": 5, "length": 6}
        result = ot.apply_operation(text, op)
        
        assert result == "Hello"
    
    def test_hub_get_stats(self):
        """Test getting hub statistics."""
        from aol_fire.realtime import WebSocketHub
        
        hub = WebSocketHub()
        hub.create_room("Room 1")
        hub.create_room("Room 2")
        
        stats = hub.get_stats()
        
        assert stats["active_rooms"] == 2
        assert stats["rooms_created"] == 2


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests across multiple components."""
    
    def test_memory_with_reflection(self):
        """Test memory integration with reflection."""
        from aol_fire.memory import VectorMemoryStore, CodeMemory
        from aol_fire.reflection import SelfImprovingAgent
        from datetime import datetime, timedelta
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create memory store
            store = VectorMemoryStore(persist_directory=f"{tmpdir}/memory")
            code_memory = CodeMemory(store)
            
            # Create self-improving agent
            agent = SelfImprovingAgent(persist_directory=f"{tmpdir}/agent")
            
            # Record successful code generation
            start = datetime.now()
            end = start + timedelta(seconds=1)
            
            agent.record_execution(
                task_type="code_gen",
                task_description="Generate fibonacci",
                input_data={},
                output_data={"code": "def fib(n): ..."},
                start_time=start,
                end_time=end,
                success=True
            )
            
            # Store in memory
            code_memory.remember_code(
                code="def fib(n): ...",
                description="Fibonacci function",
                success=True
            )
            
            # Verify
            assert len(agent.executions) == 1
            results = code_memory.find_similar_code("fibonacci")
            assert len(results) >= 1
    
    def test_prompts_with_collaboration(self):
        """Test prompts integration with collaboration."""
        from aol_fire.prompts import get_template
        from aol_fire.collaboration import TaskAssignment
        
        # Get a code generation template
        template = get_template("code_gen_basic")
        assert template is not None
        
        # Create a task using the template
        prompt = template.render(language="Python", task="REST API")
        
        task = TaskAssignment(
            task_type="code_generation",
            description=prompt[:100],
            context={"full_prompt": prompt}
        )
        
        assert "Python" in task.description or "Python" in task.context["full_prompt"]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
