// Copyright 2025 Solace Browser Authors. All rights reserved.
// Action serializer - renderer process

#ifndef SOLACE_RECORDING_ACTION_SERIALIZER_H_
#define SOLACE_RECORDING_ACTION_SERIALIZER_H_

#include <string>
#include <memory>
#include "episode_schema.h"

namespace blink {
class Element;
class Document;
}  // namespace blink

namespace solace {
namespace recording {

// Serializes user interactions into Phase B action format
class ActionSerializer {
 public:
  ActionSerializer();
  ~ActionSerializer();

  // Serialize navigation action
  Action SerializeNavigateAction(const std::string& url, int64_t timestamp_ms);

  // Serialize click action
  Action SerializeClickAction(blink::Element* element, int64_t timestamp_ms);

  // Serialize type action (text input)
  Action SerializeTypeAction(const std::string& text, int64_t timestamp_ms);

  // Serialize select action (dropdown/radio/checkbox)
  Action SerializeSelectAction(const std::string& value, int64_t timestamp_ms);

  // Serialize submit action (form submission)
  Action SerializeSubmitAction(blink::Element* form, int64_t timestamp_ms);

 private:
  // Extract semantic selector from element
  SemanticSelector ExtractSemanticSelector(blink::Element* element);

  // Extract structural selector from element
  StructuralSelector ExtractStructuralSelector(blink::Element* element);

  // Try aria-label
  SemanticSelector TryAriaLabel(blink::Element* element);

  // Try aria-describedby
  SemanticSelector TryAriaDescribedby(blink::Element* element);

  // Try data-testid
  SemanticSelector TryDataTestId(blink::Element* element);

  // Try data-qa
  SemanticSelector TryDataQa(blink::Element* element);

  // Try placeholder (for inputs)
  SemanticSelector TryPlaceholder(blink::Element* element);

  // Try alt text (for images)
  SemanticSelector TryAltText(blink::Element* element);

  // Try CSS selector (id, class, attributes)
  StructuralSelector TryCSSSelectorPath(blink::Element* element);

  // Try XPath
  StructuralSelector TryXPath(blink::Element* element);

  // Fallback: tag + position
  StructuralSelector FallbackTagPosition(blink::Element* element);

  // Format timestamp as ISO 8601
  std::string FormatTimestamp(int64_t timestamp_ms);
};

}  // namespace recording
}  // namespace solace

#endif  // SOLACE_RECORDING_ACTION_SERIALIZER_H_
