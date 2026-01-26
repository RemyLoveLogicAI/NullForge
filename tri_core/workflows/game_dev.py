"""
Game Development Workflow
=========================

Simplified workflow definitions for game development.
"""

from tri_core.models import Platform, Workflow, WorkflowStep


def create_game_design_workflow(game_concept: str) -> Workflow:
    """Create a game design workflow."""
    return Workflow(
        name="Game Design Workflow",
        description=f"Design workflow for: {game_concept}",
        steps=[
            WorkflowStep(
                name="Concept Development",
                platform=Platform.GENSPARK,
                action="develop_game_concept",
                parameters={"concept": game_concept},
            ),
            WorkflowStep(
                name="Mechanics Design",
                platform=Platform.GENSPARK,
                action="design_game_mechanics",
                parameters={"concept": game_concept},
                dependencies=[],
            ),
            WorkflowStep(
                name="Narrative Creation",
                platform=Platform.GENSPARK,
                action="create_narrative",
                parameters={"concept": game_concept},
                dependencies=[],
            ),
        ],
    )


def create_implementation_workflow(design_doc: dict) -> Workflow:
    """Create an implementation workflow."""
    return Workflow(
        name="Implementation Workflow",
        description="Code generation and implementation",
        steps=[
            WorkflowStep(
                name="Code Generation",
                platform=Platform.AOL_CLI,
                action="generate_game_code",
                parameters={"design": design_doc},
            ),
            WorkflowStep(
                name="Test Generation",
                platform=Platform.AOL_CLI,
                action="generate_tests",
                parameters={},
                dependencies=[],
            ),
        ],
    )


def create_testing_workflow(player_id: str) -> Workflow:
    """Create a testing workflow."""
    return Workflow(
        name="Testing Workflow",
        description="Game testing and validation",
        steps=[
            WorkflowStep(
                name="Setup Test Player",
                platform=Platform.CLAWDPOKE,
                action="create_player",
                parameters={"player_id": player_id},
            ),
            WorkflowStep(
                name="Run Game Tests",
                platform=Platform.CLAWDPOKE,
                action="run_tests",
                parameters={"player_id": player_id},
                dependencies=[],
            ),
            WorkflowStep(
                name="Collect Metrics",
                platform=Platform.CLAWDPOKE,
                action="collect_metrics",
                parameters={},
                dependencies=[],
            ),
        ],
    )


class GameDevelopmentWorkflow:
    """
    🎮 Game Development Workflow Manager
    
    Provides pre-built workflows for game development.
    """
    
    @staticmethod
    def design(concept: str) -> Workflow:
        """Create a design workflow."""
        return create_game_design_workflow(concept)
    
    @staticmethod
    def implement(design_doc: dict) -> Workflow:
        """Create an implementation workflow."""
        return create_implementation_workflow(design_doc)
    
    @staticmethod
    def test(player_id: str = "test_player") -> Workflow:
        """Create a testing workflow."""
        return create_testing_workflow(player_id)
    
    @staticmethod
    def full_pipeline(concept: str) -> Workflow:
        """Create a full pipeline workflow."""
        return Workflow(
            name="Full Game Development Pipeline",
            description=f"Complete pipeline for: {concept}",
            steps=[
                # Design Phase
                WorkflowStep(
                    id="design_1",
                    name="Concept Development",
                    platform=Platform.GENSPARK,
                    action="develop_concept",
                    parameters={"concept": concept},
                ),
                WorkflowStep(
                    id="design_2",
                    name="Detailed Design",
                    platform=Platform.GENSPARK,
                    action="create_design_doc",
                    parameters={},
                    dependencies=["design_1"],
                ),
                # Implementation Phase
                WorkflowStep(
                    id="impl_1",
                    name="Generate Code",
                    platform=Platform.AOL_CLI,
                    action="generate_code",
                    parameters={},
                    dependencies=["design_2"],
                ),
                WorkflowStep(
                    id="impl_2",
                    name="Generate Tests",
                    platform=Platform.AOL_CLI,
                    action="generate_tests",
                    parameters={},
                    dependencies=["impl_1"],
                ),
                # Integration Phase
                WorkflowStep(
                    id="int_1",
                    name="Game Integration",
                    platform=Platform.CLAWDPOKE,
                    action="integrate_game",
                    parameters={},
                    dependencies=["impl_1"],
                ),
                # Testing Phase
                WorkflowStep(
                    id="test_1",
                    name="Run Tests",
                    platform=Platform.CLAWDPOKE,
                    action="run_tests",
                    parameters={},
                    dependencies=["int_1", "impl_2"],
                ),
                # Feedback Phase
                WorkflowStep(
                    id="feedback_1",
                    name="Collect Feedback",
                    platform=Platform.TRINITY,
                    action="collect_feedback",
                    parameters={},
                    dependencies=["test_1"],
                ),
            ],
        )
