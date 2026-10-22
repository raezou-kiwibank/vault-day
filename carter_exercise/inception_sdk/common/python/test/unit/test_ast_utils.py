# standard libs
import ast
from unittest import TestCase

# inception sdk
import inception_sdk.common.python.ast_utils as ast_utils

API_ASSIGN_NODE = ast.Assign(
    targets=[ast.Name(id="api", ctx=ast.Store())],
    value=ast.Constant(value="4.0.0", kind=None),
    lineno=1,
)
VERSION_ASSIGN_NODE = ast.Assign(
    targets=[ast.Name(id="version", ctx=ast.Store())],
    value=ast.Constant(value="1.0.0", kind=None),
    lineno=2,
)


class AssignTargetTest(TestCase):
    def test_get_assign_node_target_name(self):
        assign_node = ast.Assign(
            targets=[ast.Name(ctx=ast.Store(), id="days_in_year")], value=ast.Constant(value=365)
        )
        target_name = ast_utils.get_assign_node_target_name(assign_node)
        self.assertEqual(target_name, "days_in_year")

    def test_get_ann_assign_node_target_name(self):
        ann_assign_node = ast.AnnAssign(
            target=ast.Name(ctx=ast.Store(), id="days_in_year"),
            annotation=ast.Name(id="int", ctx=ast.Load()),
            value=ast.Constant(value=365),
        )
        target_name = ast_utils.get_ann_assign_node_target_name(ann_assign_node)
        self.assertEqual(target_name, "days_in_year")

    def test_get_ann_assign_node_target_attribute(self):
        ann_assign_node = ast.AnnAssign(
            target=ast.Attribute(value=ast.Name(id="1"), ctx=ast.Store(), attr="days_in_year"),
            annotation=ast.Name(id="int", ctx=ast.Load()),
            value=ast.Constant(value=365),
        )
        target_name = ast_utils.get_ann_assign_node_target_name(ann_assign_node)
        self.assertEqual(target_name, "days_in_year")

    def test_get_ann_assign_node_target_subscript(self):
        ann_assign_node = ast.AnnAssign(
            target=ast.Subscript(
                value=ast.Name(id="a"),
                slice=ast.Constant(value=1),
                ctx=ast.Store(),
            ),
            annotation=ast.Name(id="int", ctx=ast.Load()),
        )
        target_name = ast_utils.get_ann_assign_node_target_name(ann_assign_node)
        self.assertEqual(target_name, "a")

    def test_get_ann_assign_node_target_name_ann_assign_node_error(self):
        ann_assign_node = ann_assign_node = ast.AnnAssign(
            target=None,
            annotation=ast.Name(id="int", ctx=ast.Load()),
            value=ast.Constant(value=365),
        )
        with self.assertRaises(ast_utils.AstHandlingException):
            ast_utils.get_ann_assign_node_target_name(ann_assign_node)


class CompareAstTest(TestCase):
    def test_compare_ast_true(self):
        test_cases = [
            {
                "description": "simple single level comparison",
                "ast_object_1": ast.Name(id="name"),
                "ast_object_2": ast.Name(id="name"),
            },
            {
                "description": "simple single level comparison with ignored attributes",
                "ast_object_1": ast.Name(id="name", lineno=1),
                "ast_object_2": ast.Name(id="name", lineno=2),
            },
            {
                "description": "simple multiple level comparison",
                "ast_object_1": ast.Attribute(value=ast.Name(id="1")),
                "ast_object_2": ast.Attribute(value=ast.Name(id="1")),
            },
            {
                "description": "complex multiple level comparison with ignored attributes",
                "ast_object_1": ast.Module(
                    body=[
                        API_ASSIGN_NODE,
                        VERSION_ASSIGN_NODE,
                    ]
                ),
                "ast_object_2": ast.Module(
                    body=[
                        ast.Assign(
                            targets=[
                                ast.Name(
                                    lineno=1,
                                    col_offset=0,
                                    end_lineno=14,
                                    end_col_offset=3,
                                    id="api",
                                    ctx=ast.Store(),
                                )
                            ],
                            value=ast.Constant(
                                lineno=1,
                                col_offset=6,
                                end_lineno=14,
                                end_col_offset=13,
                                value="4.0.0",
                                kind=None,
                            ),
                        ),
                        ast.Assign(
                            targets=[
                                ast.Name(
                                    lineno=28,
                                    col_offset=0,
                                    end_lineno=15,
                                    end_col_offset=7,
                                    id="version",
                                    ctx=ast.Store(),
                                )
                            ],
                            value=ast.Constant(
                                lineno=28,
                                col_offset=10,
                                end_lineno=15,
                                end_col_offset=17,
                                value="1.0.0",
                                kind=None,
                            ),
                        ),
                    ]
                ),
            },
        ]
        for test_case in test_cases:
            test_desc = test_case["description"]
            self.assertTrue(
                ast_utils.compare_ast(test_case["ast_object_1"], test_case["ast_object_2"]),
                f"Test case {test_desc} failed.",
            )

    def test_compare_ast_false(self):
        test_cases = [
            {
                "description": "Same Class different attributes",
                "ast_object_1": ast.Name(id="1"),
                "ast_object_2": ast.Name(id="2"),
            },
            {
                "description": "Different Class same attributes",
                "ast_object_1": ast.Name(id="1"),
                "ast_object_2": ast.Attribute(id="1"),
            },
            {
                "description": "Different attributes on value object",
                "ast_object_1": ast.Attribute(value=ast.Name(id="1")),
                "ast_object_2": ast.Attribute(value=ast.Name(id="2")),
            },
            {
                "description": "Multiple levels of attributes",
                "ast_object_1": ast.Module(
                    body=[
                        API_ASSIGN_NODE,
                        VERSION_ASSIGN_NODE,
                    ]
                ),
                "ast_object_2": ast.Module(
                    body=[
                        API_ASSIGN_NODE,
                        ast.Assign(
                            targets=[ast.Name(id="version", ctx=ast.Store())],
                            value=ast.Constant(value="1.1.0", kind=None),
                        ),
                    ]
                ),
            },
        ]

        for test_case in test_cases:
            test_desc = test_case["description"]
            self.assertFalse(
                ast_utils.compare_ast(test_case["ast_object_1"], test_case["ast_object_2"]),
                f"Test case {test_desc} failed.",
            )


class UngroupStmtsTest(TestCase):
    def test_ungroup_nodes(self):
        self.maxDiff = None
        nodes = [
            API_ASSIGN_NODE,
            VERSION_ASSIGN_NODE,
            [
                ast.Assign(
                    targets=[ast.Name(id="summary", ctx=ast.Store())],
                    value=ast.Constant(value="This is a ", kind=None),
                    lineno=3,
                ),
                ast.Expr(value=ast.Constant(value="test product."), lineno=4),
            ],
            ast.Assign(
                targets=[ast.Name(id="supported_denomination", ctx=ast.Store())],
                value=ast.Constant(value="GBP", kind=None),
                lineno=5,
            ),
            [
                ast.Assign(
                    targets=[ast.Name(id="description", ctx=ast.Store())],
                    value=ast.Constant(value="More unit tests ", kind=None),
                    lineno=6,
                ),
                ast.Expr(value=ast.Constant(value="please."), lineno=7),
            ],
        ]
        expected_output = [
            API_ASSIGN_NODE,
            VERSION_ASSIGN_NODE,
            ast.Assign(
                targets=[ast.Name(id="summary", ctx=ast.Store())],
                value=ast.Constant(value="This is a ", kind=None),
                lineno=3,
            ),
            ast.Expr(value=ast.Constant(value="test product."), lineno=4),
            ast.Assign(
                targets=[ast.Name(id="supported_denomination", ctx=ast.Store())],
                value=ast.Constant(value="GBP", kind=None),
                lineno=5,
            ),
            ast.Assign(
                targets=[ast.Name(id="description", ctx=ast.Store())],
                value=ast.Constant(value="More unit tests ", kind=None),
                lineno=6,
            ),
            ast.Expr(value=ast.Constant(value="please."), lineno=7),
        ]
        nodes = ast_utils.ungroup_stmts(nodes)
        self.assertEqual(ast.unparse(nodes), ast.unparse(expected_output))
