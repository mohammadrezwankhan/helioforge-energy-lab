"""Check browser-like script boundaries used by publication evidence verification."""

import importlib
import unittest


class HtmlScriptTests(unittest.TestCase):
    def test_script_bodies_preserve_raw_text_and_html_end_tag_boundaries(self) -> None:
        module = importlib.import_module("scripts.html_scripts")
        for ending in ["</script>", "</ScRiPt >", "</script\t>", '</script ignored="x">', "</script/>"]:
            with self.subTest(ending=ending):
                blocks = module.script_blocks('<script data-note=">">a < b && c; </script-like>' + ending)
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0].body, "a < b && c; </script-like>")
                self.assertEqual(blocks[0].attributes, {"data-note": ">"})

    def test_structured_data_attributes_are_parsed_without_rewriting_body(self) -> None:
        module = importlib.import_module("scripts.html_scripts")
        blocks = module.script_blocks(
            '<!-- <script>not executable</script> -->'
            '<SCRIPT TYPE=\'application/ld+json\' data-note=">">{"name":"A &amp; B"}</SCRIPT>'
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].attributes["type"], "application/ld+json")
        self.assertEqual(blocks[0].body, '{"name":"A &amp; B"}')

    def test_html_newline_normalization_matches_browser_script_bytes(self) -> None:
        module = importlib.import_module("scripts.html_scripts")
        self.assertEqual(module.script_blocks("<script>a\r\nb\rc</script>")[0].body, "a\nb\nc")

    def test_incomplete_script_cannot_silently_disappear_from_evidence(self) -> None:
        module = importlib.import_module("scripts.html_scripts")
        with self.assertRaises(ValueError):
            module.script_blocks("<script>window.example = 1;")


if __name__ == "__main__":
    unittest.main()
