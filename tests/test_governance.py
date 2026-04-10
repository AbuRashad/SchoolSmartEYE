from app.core.governance_layer import Action, Role, check_educational_hierarchy_access


def test_teacher_can_only_view_own_scope() -> None:
    assert check_educational_hierarchy_access(
        requester_role=Role.TEACHER,
        requester_scope_id="class-a",
        target_scope_id="class-a",
        action=Action.VIEW_CLASSROOM_FEED,
    )

    assert not check_educational_hierarchy_access(
        requester_role=Role.TEACHER,
        requester_scope_id="class-a",
        target_scope_id="class-b",
        action=Action.VIEW_CLASSROOM_FEED,
    )


def test_ministry_has_global_access() -> None:
    assert check_educational_hierarchy_access(
        requester_role=Role.MINISTRY,
        requester_scope_id="national",
        target_scope_id="any-school",
        action=Action.VIEW_SYSTEM_WIDE_ANALYTICS,
    )
