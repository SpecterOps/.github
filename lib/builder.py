import os
import urllib.parse
from collections import OrderedDict

import mdutils

from lib.loader import load_config
from lib.logger import logger


def _convert_license_name(license_name: str) -> str:
    """Convert a license name to a URL-friendly string"""
    return license_name.replace(" ", "_").replace("-", "--")


class ReadMeBuilder:
    """Build a README.md file based on a JSON file containing GitHub repository data."""
    script_path = os.path.realpath(".")
    config_path = os.path.join(script_path, "config", "config.yml")

    # SpecterOps website color palette
    COLORS = {
        "green": "02B36C",
        "blue": "2C2677",
        "violet": "0F0B38",
        "neon": "5465FF",
        "lavender": "D7D6E6",
        "red": "FF7E79",
        "blue": "A8D08D",
        "purple": "966FD6",
    }

    def __init__(self, data):
        cfg = load_config(self.config_path)
        self.featured_projects = cfg["featured"]
        self.title = cfg["copy"]["title"]
        self.introduction = cfg["copy"]["introduction"]
        self.featured = cfg["copy"]["featured"]
        self.other = cfg["copy"]["other"]
        self.banner = cfg["copy"]["banner"]

        self.slack_invite = cfg["community"]["slack"]

        self.overrides = cfg["overrides"]

        self.data = data
        self.md_file = mdutils.MdUtils(file_name="profile/README.md", title=self.title)

    def build(self, toc: bool = False) -> None:
        """
        Build the README.md file.

        **Parameters**

        ``toc``
            A boolean value to determine whether to include a table of contents
        """
        self._build_header()
        self._build_featured()
        self._build_other()
        if toc:
            self.md_file.new_table_of_contents(table_title="Contents", depth=2)
        self.md_file.create_md_file()

    def _build_header(self) -> None:
        """Build the header of the README.md file, the section above the "Featured Projects" header."""
        self.md_file.new_line(
            self.md_file.new_inline_image("SpecterOps", self.banner)
        )
        self.md_file.new_line()
        self.md_file.new_line(
            f"[![Slack](https://img.shields.io/badge/Slack-SpecterOps-{self.COLORS['green']})]({self.slack_invite})"
            " "
            "[![Twitter](https://img.shields.io/twitter/follow/specterops?style=social)](https://twitter.com/specterops)"
            " "
            "[![Mastodon](https://img.shields.io/mastodon/follow/109314317500800201?domain=https%3A%2F%2Finfosec.exchange&style=social)](https://infosec.exchange/@specterops)"
        )
        self.md_file.new_line()
        self.md_file.new_line()
        self.md_file.write(self.introduction.strip())
        self.md_file.new_line()

    def _build_featured(self) -> None:
        """Build the "Featured Projects" section of the README.md file."""
        self.md_file.new_header(level=1, title=":fire: Featured Projects")
        self.md_file.new_line(self.featured.strip())
        self.md_file.new_line()

        self.md_file.new_line("<details><summary>Expand</summary>")
        self.md_file.new_line()

        for repo in self.data.values():
            # Project may be empty if it has been made private
            if repo:
                name = repo["name"]
                owner = repo["owner"]["login"]
                if "nameWithOwner" in repo:
                    name_with_owner = repo["nameWithOwner"]
                else:
                    name_with_owner = owner + "/" + name
                description = repo["description"]
                url = repo["url"]
                homepage_url = repo["homepageUrl"]
                archived = repo["isArchived"]

                project_type = repo["type"]
                if project_type.lower() in ["r", "red"]:
                    project_type = urllib.parse.quote("Red Team")
                    project_color = self.COLORS["red"]

                if project_type.lower() in ["b", "blue"]:
                    project_type = urllib.parse.quote("Blue Team")
                    project_color = self.COLORS["blue"]

                if project_type.lower() in ["p", "purple"]:
                    project_type = urllib.parse.quote("Red & Blue Team")
                    project_color = self.COLORS["purple"]

                license_name = None
                if repo["licenseInfo"]:
                    license_name = _convert_license_name(repo["licenseInfo"]["spdxId"])

                img = None
                if repo["img"]:
                    img = f"../img/{repo['img']}"

                for project in self.overrides:
                    if project["repo"] == name.lower():
                        if "name" in project:
                            name = project["name"].strip()
                        if "description" in project:
                            logger.info(f"Overriding description for {name}")
                            description = project["description"].strip()
                        if "license" in project:
                            license_name = _convert_license_name(project["license"].strip())

                # Repo language metrics
                language_metrics = {}
                languages = repo["languages"]
                total_size = languages["totalSize"]
                for language in languages["edges"]:
                    language_name = language["node"]["name"]
                    language_size = language["size"]
                    language_percentage = round((language_size / total_size) * 100, 2)
                    language_metrics[language_name] = language_percentage
                language_metrics = OrderedDict(sorted(language_metrics.items(), key=lambda t: t[1], reverse=True))

                try:
                    top_lang = urllib.parse.quote(next(iter(language_metrics)))
                except StopIteration:
                    pass

                if repo["featured"]:
                    title = name
                    if archived:
                        title += " (Retired)"
                    self.md_file.new_header(level=2, title=title)

                    # Add badges for licenses and stats
                    badges = ""
                    if license_name:
                        badges = f"![license](https://img.shields.io/badge/license-{license_name}-{self.COLORS['green']})"
                    badges += f" ![Project Type](https://img.shields.io/badge/type-{project_type}-{project_color})"
                    badges += f" ![Slack](https://img.shields.io/badge/language-{top_lang}-{self.COLORS['neon']})"
                    badges += f" ![forks](https://img.shields.io/github/forks/{name_with_owner}?color={self.COLORS['violet']}&style=social)"
                    badges += f" ![stargazers](https://img.shields.io/github/stars/{name_with_owner}?color={self.COLORS['neon']}&style=social)"
                    self.md_file.new_line(badges)

                    self.md_file.new_line("<details><summary>More Info</summary>")

                    if img:
                        self.md_file.new_line()
                        self.md_file.new_line(
                            self.md_file.new_inline_image(name, img)
                        )

                    if not description:
                        logger.warning(f"Featured project {name_with_owner} has no description")
                    self.md_file.new_line()
                    for line in description.splitlines():
                        self.md_file.new_line(f"> {line}")

                    table_contents = [
                        "Resource", "Link",
                        "GitHub", f"<{url}>",
                    ]
                    if homepage_url:
                        table_contents.extend(["Homepage", f"<{homepage_url}>"])
                    if repo["extras"]:
                        for extra in repo["extras"]:
                            extra[0] = extra[0].capitalize()
                            table_contents.extend(extra)
                    rows = len(table_contents) // 2
                    self.md_file.new_line()
                    self.md_file.new_table(columns=2, rows=rows, text=table_contents, text_align="left")

                    self.md_file.new_line("</details>")
                    self.md_file.new_line()

        self.md_file.new_line("</details>")
        self.md_file.new_line()

    def _build_other(self) -> None:
        """Build the final section of the README.md file."""
        self.md_file.new_header(level=1, title=":purple_heart: Other Projects")
        self.md_file.new_line()
        self.md_file.new_line(self.other.strip())
        self.md_file.new_line()

        self.md_file.new_line("<details><summary>Expand</summary>")
        self.md_file.new_line()

        for repo in self.data.values():
            if repo:
                name = repo["name"]
                owner = repo["owner"]["login"]
                if "nameWithOwner" in repo:
                    name_with_owner = repo["nameWithOwner"]
                else:
                    name_with_owner = owner + "/" + name
                url = repo["url"]
                description = repo["description"]

                if not repo["featured"]:
                    self.md_file.new_line(f"- [{name_with_owner}]({url})")
                    if description:
                        self.md_file.new_line(f"  - {description}")

        self.md_file.new_line("</details>")
        self.md_file.new_line()
