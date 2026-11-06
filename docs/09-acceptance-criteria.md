# Acceptance criteria (Given / When / Then)

[← Back to the index](README.md)

```gherkin
Feature: Plan
  Scenario: Successful review consumes one slot
    Given 3 reviews completed this month and none running
    When Chiara requests a review and it completes after 12 s
    Then the plan shows 6 available

  Scenario: Failed review does not consume
    Given 3 completed this month
    When a review fails with an AI error
    Then the plan shows 7 available

  Scenario: Running reviews reserve slots
    Given 9 completed and 0 running
    When Chiara requests a review of the NDA
    Then Riccardo cannot request a review of the Loan agreement
    And he sees that 9 completed + 1 in progress = all 10 in use
    And he sees that the review in progress frees its slot if it fails
    And he sees that his request has not been saved

  Scenario: Reservation released on failure
    Given 9 completed and 1 running
    When the running review times out
    Then 1 review is available

  Scenario: Strict block when the plan is used up
    Given 10 completed this month
    When any lawyer opens any document
    Then the request button is disabled
    And the reset date "1 Dec 2026, 00:00 Rome time" is shown
    And a direct POST returns 409 PLAN_EXHAUSTED and creates no review

  Scenario: Month boundary counts in the month of the request
    Given the clock is 30 Nov 2026 23:59:50 Rome time
    When a review requested now completes at 1 Dec 00:00:05
    Then it counts in November
    And December shows 10 available

  Scenario: A review running at midnight does not reserve a slot in the new month
    Given 9 completed in November and 1 review requested on 30 Nov at 23:59:30 still running
    When the clock reaches 1 Dec 00:00:00 Rome time
    Then December shows 10 available

Feature: One review in progress per document
  Scenario: Concurrent requests on the same document
    Given no review is running on the SaaS agreement
    When Chiara and Sofia request it at the same time
    Then exactly one review is created
    And the other lawyer receives REVIEW_IN_PROGRESS and follows it

  Scenario: Stale running row does not block
    Given a review of the NDA is still running in the DB but past its deadline
    When Sofia requests a review of the NDA
    Then the old review becomes failed with reason timed_out
    And a new review is created

Feature: Deadline
  Scenario: Late completion is ignored
    Given a review requested at T0
    When the AI completes at T0 + 95 s
    Then the review is failed with reason timed_out
    And the plan is unchanged
    And no late finding is stored

  Scenario: Boundary at exactly 60 s
    When completion is processed at T0 + 60.000 s
    Then the review is failed with reason timed_out

  Scenario: Completion just before the deadline
    When completion is processed at T0 + 59.999 s
    Then the review is completed and consumes one slot

  Scenario: Retry is a new review
    Given a failed review of the Loan agreement
    When Chiara clicks Retry and confirms
    Then a new review with a new id and a new deadline is created
    And the failed review remains stored with status failed

Feature: Reading results
  Scenario: Partial findings of a running review are marked as partial
    Given a running review with 2 findings received
    Then each finding is tagged Partial
    And no severity totals are shown
    And the incomplete banner is visible

  Scenario: Findings of a failed review are not displayed
    Given a review that failed after 2 findings
    Then the panel shows only the failure status, "not counted" and Retry
    And none of the 2 findings is displayed
    And GET /api/reviews/{id} returns an empty findings list

  Scenario: Previous review skips failed reviews
    Given the Lease v2 has a review completed on 2 Nov and a review that failed on 4 Nov
    When a new review is running
    Then the 2 Nov review is shown as "Previous result · no longer current"
    And nothing from the 4 Nov review is displayed

  Scenario: Superseded document is labelled as a previous version
    When a lawyer views the document list
    Then the 3 Sep lease is labelled "Previous version · superseded by the version of 24 Sep"
    And, while Q6 is open, its Request review button works like any other document's

  Scenario: Completed review of a superseded document
    Given the Lease v1 has a completed review
    When a lawyer opens the Lease v1
    Then its completed review is displayed like any other

  Scenario: Completed with no findings
    When the review of the Consulting agreement completes
    Then the panel shows "Completed · no clauses flagged" with the disclaimer
    And the badge differs from "Not reviewed"

  Scenario: Previous review during a new run
    Given the Lease v2 has a completed review from 2 Nov
    When a new review is running
    Then the 2 Nov review is shown under "Previous result · no longer current"
    And each of its findings is tagged Previous
    And it is never merged with the running findings

  Scenario: Final ordering
    When a review of the Franchise agreement completes
    Then findings are ordered high, medium, low
    And within a severity they are in natural clause order with "General" last

  Scenario: Missing clause
    Then a finding with no clause shows "General (no specific clause)" and the missing-excerpt note

Feature: Identity
  Scenario: Unknown lawyer
    When a POST carries an unknown X-Lawyer-Id
    Then it returns 400 UNKNOWN_LAWYER and creates no review
```
