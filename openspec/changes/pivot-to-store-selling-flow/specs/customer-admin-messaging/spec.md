## Purpose

Defines how authenticated customers contact store admins from the storefront while keeping admin response workflow simple and ready for later expansion.

## ADDED Requirements

### Requirement: Authenticated customers can message store admins
The system SHALL allow authenticated non-admin users to submit messages to the store admin from a customer-facing account or support surface.

#### Scenario: Customer sends message
- **WHEN** an authenticated non-admin user submits a valid message to the store admin
- **THEN** the system stores the message with the sender, subject or context, body, and unread admin state

#### Scenario: Empty message is rejected
- **WHEN** an authenticated non-admin user submits a blank or invalid message
- **THEN** the system rejects the message with validation feedback and does not create a message record

#### Scenario: Guest message requires login
- **WHEN** a guest attempts to send a message to the store admin
- **THEN** the system requires login or signup before accepting the message

### Requirement: Admins can read customer messages
The system SHALL provide an admin-protected way to list and inspect customer messages.

#### Scenario: Admin lists messages
- **WHEN** an authenticated admin opens or requests the customer message list
- **THEN** the system returns customer messages with sender identity, message content summary, read state, and timestamps

#### Scenario: Non-admin cannot list messages
- **WHEN** a guest or authenticated non-admin attempts to access customer messages
- **THEN** the system rejects access with an authorization error

#### Scenario: Admin marks message read
- **WHEN** an authenticated admin marks a customer message as read
- **THEN** the system updates the message read state without deleting the message

### Requirement: Customer messages are private
The system SHALL prevent customers from reading other customers' messages and SHALL keep admin-only message state out of public catalog responses.

#### Scenario: Customer views own message history
- **WHEN** authenticated customer message history is available and the customer requests it
- **THEN** the system returns only messages sent by that customer

#### Scenario: Customer cannot read another customer's message
- **WHEN** an authenticated non-admin user attempts to access a message sent by another user
- **THEN** the system rejects access without exposing the message content
