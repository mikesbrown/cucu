Feature: Repeating steps
  As a developer I want the test writers to be able to repeat steps in a loop.

  Scenario: User can repeat a set of steps N times
    Given I repeat "3" times the following steps with iteration variable "ITER":
      """
      Then I create the directory at "{SCENARIO_RESULTS_DIR}/files/iter-\{ITER\}"
      """
     Then I should see the directory at "{SCENARIO_RESULTS_DIR}/files/iter-1"
      And I should see the directory at "{SCENARIO_RESULTS_DIR}/files/iter-2"
      And I should see the directory at "{SCENARIO_RESULTS_DIR}/files/iter-3"

  Scenario: User can repeat a set of web steps N times
    Given I start a webserver at directory "data/www" and save the port to the variable "PORT"
      And I open a browser at the url "http://{HOST_ADDRESS}:{PORT}/counter.html"
     When I repeat "3" times the following steps with iteration variable "ITER":
      """
      Then I wait to click the button "count"
      """
      And I wait to see the value "3" in the input "count at"