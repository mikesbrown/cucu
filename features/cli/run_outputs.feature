Feature: Run outputs
  As a developer I want the user to the expected console and filesystem outputs
  when running with certain flags/feature files.

  Scenario: User can --dry-run a passing scenario
    Given I run the command "cucu run data/features/feature_with_passing_scenario.feature --dry-run --results {CUCU_RESULTS_DIR}/passing_feature_dry_run_results" and save stdout to "STDOUT", stderr to "STDERR", exit code to "EXIT_CODE"
     Then I should see "{EXIT_CODE}" is equal to "0"
      And I should not see the directory at "{CUCU_RESULTS_DIR}/passing_feature_dry_run_results"
      And I should see "{STDOUT}" matches the following
      """
      Feature: Feature with passing scenario

        Scenario: Just a scenario that passes
          Given I echo "nothing to see here"

      0 features passed, 0 failed, 0 skipped, 1 untested
      0 scenarios passed, 0 failed, 0 skipped, 1 untested
      0 steps passed, 0 failed, 0 skipped, 0 undefined, 1 untested
      [\s\S]*
      """
      And I should see "{STDERR}" is empty

  Scenario: User gets expected output when running steps with substeps
    Given I run the command "cucu run data/features/scenario_with_substeps.feature --results {CUCU_RESULTS_DIR}/substeps-results" and save stdout to "STDOUT", stderr to "STDERR", exit code to "EXIT_CODE"
     Then I should see "{EXIT_CODE}" is equal to "0"
      And I should see "{STDOUT}" matches the following
      """
      [\s\S]*
      Feature: Feature with substeps

        Scenario: Scenario that uses a step with substeps
            ⤷ When I do nothing             .*
            ⤷  And I do nothing             .*
            ⤷  And I do nothing             .*
          Given I use a step with substeps  .*

      1 feature passed, 0 failed, 0 skipped
      1 scenario passed, 0 failed, 0 skipped
      1 step passed, 0 failed, 0 skipped, 0 undefined
      [\s\S]*
      """
      And I should see "{STDERR}" is empty

  Scenario: User gets expected non zero exit code when a scenario fails
    Given I run the command "cucu run data/features/feature_with_failing_scenario.feature --results {CUCU_RESULTS_DIR}/failing-scenario-results" and save stdout to "STDOUT", stderr to "STDERR", exit code to "EXIT_CODE"
     Then I should see "{EXIT_CODE}" is equal to "1"
      And I should see "{STDOUT}" matches the following
      """
      Feature: Feature with failing scenario

        Scenario: Just a scenario that fails
          Given I fail .*s
      Traceback \(most recent call last\):
      [\s\S]*
      RuntimeError: step fails on purpose
      [\s\S]*
      Failing scenarios:
        data/features/feature_with_failing_scenario.feature:3  Just a scenario that fails
      [\s\S]*
      0 features passed, 1 failed, 0 skipped
      0 scenarios passed, 1 failed, 0 skipped
      0 steps passed, 1 failed, 0 skipped, 0 undefined
      [\s\S]*
      """
      And I should see "{STDERR}" is equal to the following
      """
      Error: test run failed, see above for details

      """

  Scenario: User can run a scenario with background which uses a step with substeps
    Given I run the command "cucu run data/features/feature_with_background_using_substeps.feature --results {CUCU_RESULTS_DIR}/background-with-substeps-results" and save stdout to "STDOUT", stderr to "STDERR", exit code to "EXIT_CODE"
     Then I should see "{EXIT_CODE}" is equal to "0"
      And I should see "{STDOUT}" matches the following
      """
      Feature: Feature with background using substeps

        Scenario: Scenario which now has a background using a step with substeps
      first line of the background

          Given I echo "first line of the background"               #  in .*
            ⤷ When I open a browser at the url "https://www.google.com/search"  #  in .*
            ⤷  And I wait to write "define: kittens" into the input "Search"    #  in .*
            ⤷  And I click the button "Google Search"                           #  in .*
            And I search for "define: kittens" on google search                 #  in .*
      This is from the scenario

           When I echo "This is from the scenario"                              #  in .*

      1 feature passed, 0 failed, 0 skipped
      1 scenario passed, 0 failed, 0 skipped
      3 steps passed, 0 failed, 0 skipped, 0 undefined
      [\s\S]*
      """
      And I should see "{STDERR}" is empty