from __future__ import annotations

import unittest

from agentic.tools import web_search as web_search_module


class DuckDuckGoHtmlSearchTests(unittest.TestCase):
    def test_duckduckgo_html_parser_extracts_result_links(self) -> None:
        html = """
        <html><body>
          <div class="result results_links">
            <a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa">Example A</a>
            <a class="result__snippet">First snippet</a>
          </div>
          <div class="result results_links">
            <a rel="nofollow" class="result__a" href="https://example.com/b">Example B</a>
            <div class="result__snippet">Second <b>snippet</b></div>
          </div>
        </body></html>
        """

        results = web_search_module._parse_duckduckgo_html(html, 5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["url"], "https://example.com/a")
        self.assertEqual(results[0]["title"], "Example A")
        self.assertEqual(results[1]["snippet"], "Second snippet")

    def test_bing_html_parser_decodes_redirect_links(self) -> None:
        html = """
        <ol>
          <li class="b_algo">
            <h2><a href="https://www.bing.com/ck/a?u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS9mb3J1bQ">Example Forum</a></h2>
            <div class="b_caption"><p>Forum snippet</p></div>
          </li>
        </ol>
        """

        results = web_search_module._parse_bing_html(html, 5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com/forum")
        self.assertEqual(results[0]["title"], "Example Forum")
        self.assertEqual(results[0]["snippet"], "Forum snippet")


if __name__ == "__main__":
    unittest.main()
