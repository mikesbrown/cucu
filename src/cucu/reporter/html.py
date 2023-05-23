import glob
import json
import os
import shutil
import sys
import urllib
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as escape_

import jinja2

from cucu import format_gherkin_table, logger
from cucu.config import CONFIG
from cucu.reporter.parser import parse_log_to_html


def escape(data):
    if data is None:
        return None

    return escape_(data, {'"': "&quot;"}).rstrip()


def process_tags(element):
    """
    process tags in the element provided (scenario or feature) and basically
    convert the tags to a simple @xxx representation.
    """
    prepared_tags = []

    if "tags" not in element:
        return

    for tag in element["tags"]:
        tag = f"@{tag}"

        # process custom tag handlers
        for regex, handler in CONFIG["__CUCU_HTML_REPORT_TAG_HANDLERS"].items():
            if regex.match(tag):
                tag = handler(tag)

        prepared_tags.append(tag)

    element["tags"] = " ".join(prepared_tags)


def generate(results, basepath, only_failures=False):
    """
    generate an HTML report for the results provided.
    """

    show_status = CONFIG["CUCU_SHOW_STATUS"] == "true"

    features = []

    run_json_filepaths = list(glob.iglob(os.path.join(results, "*run.json")))
    logger.info(
        f"Starting to process {len(run_json_filepaths)} files for report"
    )

    for run_json_filepath in run_json_filepaths:
        with open(run_json_filepath, "rb") as index_input:
            try:
                features += json.loads(index_input.read())
                if show_status:
                    print("r", end="", flush=True)
            except Exception as exception:
                if show_status:
                    print("")  # add a newline before logger
                logger.warn(
                    f"unable to read file {run_json_filepath}, got error: {exception}"
                )

    # copy the external dependencies to the reports destination directory
    cucu_dir = os.path.dirname(sys.modules["cucu"].__file__)
    external_dir = os.path.join(cucu_dir, "reporter", "external")
    shutil.copytree(external_dir, os.path.join(basepath, "external"))

    #
    # augment existing test run data with:
    #  * features & scenarios with `duration` attribute computed by adding all
    #    step durations.
    #  * add `image` attribute to a step if it has an underlying .png image.
    #
    reported_features = []
    for feature in features:
        if show_status:
            print("F", end="", flush=True)
        scenarios = []

        if feature["status"] != "untested" and "elements" in feature:
            scenarios = feature["elements"]

        if only_failures and feature["status"] != "failed":
            continue

        feature_duration = 0
        total_scenarios = 0
        total_scenarios_passed = 0
        total_scenarios_failed = 0
        total_scenarios_skipped = 0
        feature_started_at = None

        reported_features.append(feature)
        process_tags(feature)

        if feature["status"] not in ["skipped", "untested"]:
            # copy each feature directories contents over to the report directory
            src_feature_filepath = os.path.join(results, feature["name"])
            dst_feature_filepath = os.path.join(basepath, feature["name"])
            shutil.copytree(
                src_feature_filepath, dst_feature_filepath, dirs_exist_ok=True
            )

        for scenario in scenarios:
            if show_status:
                print("S", end="", flush=True)

            process_tags(scenario)

            sub_headers = []
            for handler in CONFIG[
                "__CUCU_HTML_REPORT_SCENARIO_SUBHEADER_HANDLER"
            ]:
                sub_headers.append(handler(scenario))
            scenario["sub_headers"] = "<br/>".join(sub_headers)

            scenario_duration = 0
            total_scenarios += 1
            total_steps = 0

            if "status" not in scenario:
                total_scenarios_skipped += 1
            elif scenario["status"] == "passed":
                total_scenarios_passed += 1
            elif scenario["status"] == "failed":
                total_scenarios_failed += 1
            elif scenario["status"] == "skipped":
                total_scenarios_skipped += 1

            scenario_filepath = os.path.join(
                basepath, feature["name"], scenario["name"]
            )

            step_index = 0
            scenario_started_at = None
            for step in scenario["steps"]:
                if show_status:
                    print("s", end="", flush=True)
                total_steps += 1
                image_filename = (
                    f"{step_index} - {step['name'].replace('/', '_')}.png"
                )
                image_filepath = os.path.join(scenario_filepath, image_filename)

                if step["name"].startswith("#"):
                    step["heading_level"] = "h4"

                if os.path.exists(image_filepath):
                    step["image"] = urllib.parse.quote(image_filename)

                if "result" in step:
                    if step["result"]["status"] in ["failed", "passed"]:
                        timestamp = datetime.fromisoformat(
                            step["result"]["timestamp"]
                        )
                        step["result"]["timestamp"] = timestamp

                        if scenario_started_at == None:
                            scenario_started_at = timestamp
                            scenario["started_at"] = timestamp
                        step["result"][
                            "time_offset"
                        ] = datetime.utcfromtimestamp(
                            (timestamp - scenario_started_at).total_seconds()
                        )

                    scenario_duration += step["result"]["duration"]

                    if "error_message" in step["result"] and step["result"][
                        "error_message"
                    ] == [None]:
                        step["result"]["error_message"] = [""]

                if "text" in step and not isinstance(step["text"], list):
                    step["text"] = [step["text"]]

                # prepare by joining into one big chunk here since we can't do it in the Jinja template
                if "text" in step:
                    text_indent = "       "
                    step["text"] = "\n".join(
                        [text_indent + '"""']
                        + [f"{text_indent}{x}" for x in step["text"]]
                        + [text_indent + '"""']
                    )

                # prepare by joining into one big chunk here since we can't do it in the Jinja template
                if "table" in step:
                    step["table"] = format_gherkin_table(
                        step["table"]["rows"],
                        step["table"]["headings"],
                        "       ",
                    )

                step_index += 1
            logs_dir = os.path.join(scenario_filepath, "logs")

            if os.path.exists(logs_dir):
                log_files = []
                for log_file in glob.iglob(os.path.join(logs_dir, "*.*")):
                    if show_status:
                        print("l", end="", flush=True)
                    log_filepath = log_file.removeprefix(
                        f"{scenario_filepath}/"
                    )

                    if ".console." in log_filepath:
                        log_filepath += ".html"

                    log_files.append(
                        {
                            "filepath": log_filepath,
                            "name": os.path.basename(log_file),
                        }
                    )

                scenario["logs"] = log_files

            scenario["total_steps"] = total_steps
            if scenario_started_at == None:
                scenario["started_at"] = ""
            else:
                if feature_started_at == None:
                    feature_started_at = scenario_started_at
                    feature["started_at"] = feature_started_at

                scenario["time_offset"] = datetime.utcfromtimestamp(
                    (scenario_started_at - feature_started_at).total_seconds()
                )

                for log_file in [
                    x for x in log_files if ".console." in x["name"]
                ]:
                    if show_status:
                        print("c", end="", flush=True)

                    log_file_filepath = os.path.join(
                        scenario_filepath, "logs", log_file["name"]
                    )

                    input_file = Path(log_file_filepath)
                    output_file = Path(log_file_filepath + ".html")
                    output_file.write_text(
                        parse_log_to_html(input_file.read_text())
                    )

            scenario["duration"] = scenario_duration
            feature_duration += scenario_duration

        if feature_started_at == None:
            feature["started_at"] = ""

        feature["total_steps"] = sum([x["total_steps"] for x in scenarios])
        feature["duration"] = sum([x["duration"] for x in scenarios])

        feature["total_scenarios"] = total_scenarios
        feature["total_scenarios_passed"] = total_scenarios_passed
        feature["total_scenarios_failed"] = total_scenarios_failed
        feature["total_scenarios_skipped"] = total_scenarios_skipped

    keys = [
        "total_scenarios",
        "total_scenarios_passed",
        "total_scenarios_failed",
        "total_scenarios_skipped",
        "duration",
    ]
    grand_totals = {}
    for k in keys:
        grand_totals[k] = sum([x[k] for x in reported_features])

    package_loader = jinja2.PackageLoader("cucu.reporter", "templates")
    templates = jinja2.Environment(loader=package_loader)
    if show_status:
        print("")  # add a newline to end status

    def urlencode(string):
        """
        handles encoding specific characters in the names of features/scenarios
        so they can be used in a URL. NOTICE: we're not handling spaces since
        the browser handles those already.

        """
        return (
            string.replace('"', "%22").replace("'", "%27").replace("#", "%23")
        )

    templates.globals.update(escape=escape, urlencode=urlencode)

    index_template = templates.get_template("index.html")
    rendered_index_html = index_template.render(
        features=reported_features,
        grand_totals=grand_totals,
        title="Cucu HTML Test Report",
        basepath=basepath,
        dir_depth="",
    )

    index_output_filepath = os.path.join(basepath, "index.html")
    with open(index_output_filepath, "wb") as output:
        output.write(rendered_index_html.encode("utf8"))

    flat_template = templates.get_template("flat.html")
    rendered_flat_html = flat_template.render(
        features=reported_features,
        grand_totals=grand_totals,
        title="Flat HTML Test Report",
        basepath=basepath,
        dir_depth="",
    )

    flat_output_filepath = os.path.join(basepath, "flat.html")
    with open(flat_output_filepath, "wb") as output:
        output.write(rendered_flat_html.encode("utf8"))

    feature_template = templates.get_template("feature.html")

    for feature in reported_features:
        feature_basepath = os.path.join(basepath, feature["name"])
        os.makedirs(feature_basepath, exist_ok=True)

        scenarios = []
        if feature["status"] != "untested" and "elements" in feature:
            scenarios = feature["elements"]

        rendered_feature_html = feature_template.render(
            feature=feature,
            scenarios=scenarios,
            dir_depth="",
            title=feature.get("name", "Cucu results"),
        )

        feature_output_filepath = os.path.join(
            basepath, f'{feature["name"]}.html'
        )

        with open(feature_output_filepath, "wb") as output:
            output.write(rendered_feature_html.encode("utf8"))

        scenario_template = templates.get_template("scenario.html")

        for scenario in scenarios:
            steps = scenario["steps"]
            scenario_basepath = os.path.join(feature_basepath, scenario["name"])
            os.makedirs(scenario_basepath, exist_ok=True)

            scenario_output_filepath = os.path.join(
                scenario_basepath, "index.html"
            )

            rendered_scenario_html = scenario_template.render(
                basepath=results,
                feature=feature,
                path_exists=os.path.exists,
                scenario=scenario,
                steps=steps,
                title=scenario.get("name", "Cucu results"),
                dir_depth="../../",
            )

            with open(scenario_output_filepath, "wb") as output:
                output.write(rendered_scenario_html.encode("utf8"))

    return os.path.join(basepath, "index.html")
