// Copyright 2025 Solace Browser Authors. All rights reserved.
// Action serializer implementation

#include "action_serializer.h"
#include "base/time/time.h"
#include "base/strings/string_number_conversions.h"

namespace solace {
namespace recording {

ActionSerializer::ActionSerializer() {}

ActionSerializer::~ActionSerializer() {}

Action ActionSerializer::SerializeNavigateAction(const std::string& url,
                                                 int64_t timestamp_ms) {
  Action action;
  action.type = ActionType::NAVIGATE;
  action.timestamp = FormatTimestamp(timestamp_ms);
  action.value = url;

  // Target for navigation is the URL itself
  action.target.semantic.type = SelectorType::URL;
  action.target.semantic.value = url;
  action.target.structural.type = SelectorType::URL;
  action.target.structural.value = url;

  return action;
}

Action ActionSerializer::SerializeClickAction(blink::Element* element,
                                              int64_t timestamp_ms) {
  Action action;
  action.type = ActionType::CLICK;
  action.timestamp = FormatTimestamp(timestamp_ms);
  action.value = "";  // Click has no text value

  // Extract selectors
  action.target.semantic = ExtractSemanticSelector(element);
  action.target.structural = ExtractStructuralSelector(element);

  return action;
}

Action ActionSerializer::SerializeTypeAction(const std::string& text,
                                             int64_t timestamp_ms) {
  Action action;
  action.type = ActionType::TYPE;
  action.timestamp = FormatTimestamp(timestamp_ms);
  action.value = text;

  return action;
}

Action ActionSerializer::SerializeSelectAction(const std::string& value,
                                               int64_t timestamp_ms) {
  Action action;
  action.type = ActionType::SELECT;
  action.timestamp = FormatTimestamp(timestamp_ms);
  action.value = value;

  return action;
}

Action ActionSerializer::SerializeSubmitAction(blink::Element* form,
                                               int64_t timestamp_ms) {
  Action action;
  action.type = ActionType::SUBMIT;
  action.timestamp = FormatTimestamp(timestamp_ms);
  action.value = "";

  // Extract form selectors
  action.target.semantic = ExtractSemanticSelector(form);
  action.target.structural = ExtractStructuralSelector(form);

  return action;
}

SemanticSelector ActionSerializer::ExtractSemanticSelector(
    blink::Element* element) {
  if (!element) {
    return {SelectorType::TAG_POSITION, ""};
  }

  // Try selectors in priority order
  auto selector = TryAriaLabel(element);
  if (!selector.value.empty()) return selector;

  selector = TryDataTestId(element);
  if (!selector.value.empty()) return selector;

  selector = TryDataQa(element);
  if (!selector.value.empty()) return selector;

  selector = TryPlaceholder(element);
  if (!selector.value.empty()) return selector;

  selector = TryAltText(element);
  if (!selector.value.empty()) return selector;

  // Fallback
  return {SelectorType::TAG_POSITION, ""};
}

StructuralSelector ActionSerializer::ExtractStructuralSelector(
    blink::Element* element) {
  if (!element) {
    return {SelectorType::TAG_POSITION, ""};
  }

  // Try CSS selector first
  auto selector = TryCSSSelectorPath(element);
  if (!selector.value.empty()) return selector;

  // Try XPath
  selector = TryXPath(element);
  if (!selector.value.empty()) return selector;

  // Fallback to tag + position
  return FallbackTagPosition(element);
}

SemanticSelector ActionSerializer::TryAriaLabel(blink::Element* element) {
  // In real implementation, call element->getAttribute("aria-label")
  return {SelectorType::ARIA_LABEL, ""};
}

SemanticSelector ActionSerializer::TryAriaDescribedby(
    blink::Element* element) {
  return {SelectorType::ARIA_DESCRIBEDBY, ""};
}

SemanticSelector ActionSerializer::TryDataTestId(blink::Element* element) {
  // In real implementation, call element->getAttribute("data-testid")
  return {SelectorType::DATA_TESTID, ""};
}

SemanticSelector ActionSerializer::TryDataQa(blink::Element* element) {
  return {SelectorType::DATA_QA, ""};
}

SemanticSelector ActionSerializer::TryPlaceholder(blink::Element* element) {
  return {SelectorType::PLACEHOLDER, ""};
}

SemanticSelector ActionSerializer::TryAltText(blink::Element* element) {
  return {SelectorType::ALT_TEXT, ""};
}

StructuralSelector ActionSerializer::TryCSSSelectorPath(
    blink::Element* element) {
  // In real implementation, generate CSS selector path
  return {SelectorType::CSS_SELECTOR, ""};
}

StructuralSelector ActionSerializer::TryXPath(blink::Element* element) {
  return {SelectorType::XPATH, ""};
}

StructuralSelector ActionSerializer::FallbackTagPosition(
    blink::Element* element) {
  return {SelectorType::TAG_POSITION, ""};
}

std::string ActionSerializer::FormatTimestamp(int64_t timestamp_ms) {
  // Convert milliseconds since epoch to ISO 8601 format
  base::Time time = base::Time::FromJsTime(static_cast<double>(timestamp_ms));
  return time.ToStringWithoutLocalOffset() + "Z";
}

}  // namespace recording
}  // namespace solace
