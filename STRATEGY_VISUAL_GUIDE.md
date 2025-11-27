# Click Strategy System - Visual Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     extract_iapd_zip.py                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         extract_zip_links_selenium()               │  │
│  │         • Load page                                 │  │
│  │         • Apply click strategies                    │  │
│  │         • Extract ZIP links                         │  │
│  └──────────────┬──────────────────────────────────────┘  │
│                 │                                           │
│                 ▼                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         click_by_strategies()                       │  │
│  │         Try strategies in order until success       │  │
│  └──────────────┬──────────────────────────────────────┘  │
│                 │                                           │
│                 ▼                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         find_element_by_strategy()                  │  │
│  │         • text    → XPath text search               │  │
│  │         • class   → By.CLASS_NAME                   │  │
│  │         • css     → By.CSS_SELECTOR                 │  │
│  │         • xpath   → By.XPATH                        │  │
│  │         • id      → By.ID                           │  │
│  └──────────────┬──────────────────────────────────────┘  │
│                 │                                           │
│                 ▼                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         click_element()                             │  │
│  │         • Scroll into view                          │  │
│  │         • Click (with JS fallback)                  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Strategy Flow

```
┌─────────────────┐
│  User Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Strategies Defined (Priority Order)    │
│  1. class: "accordion-header"           │
│  2. css: "div.accordion-header"         │
│  3. text: "Form ADV Part 1"             │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│  Try Strategy 1 │──No──>│  Try Strategy 2 │──┐
└────────┬────────┘       └────────┬────────┘  │
         │Yes                      │Yes         │No
         │                         │            │
         ▼                         ▼            ▼
┌─────────────────┐       ┌─────────────────┐  │
│  Click Element  │       │  Click Element  │  │
└────────┬────────┘       └────────┬────────┘  │
         │                         │            │
         ▼                         ▼            ▼
┌─────────────────────────────────────────────────┐
│          Extract ZIP Links                      │
└─────────────────────────────────────────────────┘
```

## Strategy Types Detail

```
┌────────────────────────────────────────────────────────────┐
│                    STRATEGY TYPES                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  TEXT                                                      │
│  ├─ Type: 'text'                                          │
│  ├─ Value: "Form ADV Part 1"                              │
│  ├─ Finds: Any element containing text (case-insensitive) │
│  └─ Best for: Stable text content                         │
│                                                            │
│  CLASS                                                     │
│  ├─ Type: 'class'                                         │
│  ├─ Value: "accordion-header"                             │
│  ├─ Finds: Elements with CSS class                        │
│  └─ Best for: Semantic HTML classes                       │
│                                                            │
│  CSS                                                       │
│  ├─ Type: 'css'                                           │
│  ├─ Value: "div.accordion-header"                         │
│  ├─ Finds: CSS selector matches                           │
│  └─ Best for: Complex selectors, specificity              │
│                                                            │
│  XPATH                                                     │
│  ├─ Type: 'xpath'                                         │
│  ├─ Value: "//div[@class='accordion-header']"            │
│  ├─ Finds: XPath expression matches                       │
│  └─ Best for: Complex queries, parent/sibling relations   │
│                                                            │
│  ID                                                        │
│  ├─ Type: 'id'                                            │
│  ├─ Value: "expand-button"                                │
│  ├─ Finds: Element with HTML ID                           │
│  └─ Best for: Unique identifiers                          │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Usage Patterns

### Pattern 1: Single Strategy (CLI)
```
┌──────────────────────────────────────────┐
│  python extract_iapd_zip.py \            │
│    --click-strategy class \              │
│    --click-value "accordion-header"      │
└──────────────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │  Try Strategy    │
        │  class: header   │
        └────────┬─────────┘
                 │
          ┌──────┴──────┐
          │             │
        Success       Fail
          │             │
          ▼             ▼
     ┌────────┐    ┌────────┐
     │ Extract│    │ Report │
     │  ZIPs  │    │ Error  │
     └────────┘    └────────┘
```

### Pattern 2: Multiple Strategies (Fallback Chain)
```
┌─────────────────────────────────────────────┐
│  strategies = [                             │
│    {'type': 'class', 'value': 'header'},    │
│    {'type': 'css', 'value': 'div.header'},  │
│    {'type': 'text', 'value': 'Form ADV'},   │
│  ]                                          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Try Strategy 1 │
        │ (class)        │
        └────┬───────────┘
             │
      ┌──────┴──────┐
      │             │
    Success       Fail
      │             │
      │             ▼
      │    ┌────────────────┐
      │    │ Try Strategy 2 │
      │    │ (css)          │
      │    └────┬───────────┘
      │         │
      │  ┌──────┴──────┐
      │  │             │
      │Success       Fail
      │  │             │
      │  │             ▼
      │  │    ┌────────────────┐
      │  │    │ Try Strategy 3 │
      │  │    │ (text)         │
      │  │    └────┬───────────┘
      │  │         │
      │  │  ┌──────┴──────┐
      │  │  │             │
      │  │Success       Fail
      │  │  │             │
      └──┴──┴──┐          │
              │          │
              ▼          ▼
         ┌────────┐  ┌────────┐
         │Extract │  │ Error  │
         │  ZIPs  │  │ Report │
         └────────┘  └────────┘
```

### Pattern 3: Batch Processing
```
┌────────────────────────────────────────┐
│        batch_config.json               │
│                                        │
│  {                                     │
│    "pages": [                          │
│      {                                 │
│        "name": "IAPD",                 │
│        "strategies": [...]             │
│      },                                │
│      {                                 │
│        "name": "Page2",                │
│        "strategies": [...]             │
│      }                                 │
│    ]                                   │
│  }                                     │
└────────────┬───────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │ batch_extract  │
    │   .py          │
    └────────┬───────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│ Process  │  │ Process  │
│  Page 1  │  │  Page 2  │
└────┬─────┘  └────┬─────┘
     │             │
     ▼             ▼
┌──────────┐  ┌──────────┐
│ Extract  │  │ Extract  │
│  ZIPs    │  │  ZIPs    │
└────┬─────┘  └────┬─────┘
     │             │
     └──────┬──────┘
            ▼
   ┌─────────────────┐
   │ batch_results   │
   │   .json         │
   └─────────────────┘
```

## Element Finding Process

```
find_element_by_strategy()
         │
         ▼
    ┌─────────┐
    │ Strategy│
    │  Type?  │
    └────┬────┘
         │
    ┌────┴────┬────────┬────────┬──────┐
    │         │        │        │      │
    ▼         ▼        ▼        ▼      ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────┐
│ text │ │class │ │ css  │ │xpath │ │ id │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └─┬──┘
   │        │        │        │       │
   │   Convert to Selenium By locators  │
   │        │        │        │       │
   └────────┴────────┴────────┴───────┘
                     │
                     ▼
           ┌──────────────────┐
           │ driver.find_     │
           │   elements()     │
           └────────┬─────────┘
                    │
                    ▼
           ┌──────────────────┐
           │ Filter visible   │
           │ & clickable      │
           └────────┬─────────┘
                    │
             ┌──────┴──────┐
             │             │
          Found         Not Found
             │             │
             ▼             ▼
      ┌──────────┐   ┌──────────┐
      │  Return  │   │  Return  │
      │ Element  │   │   None   │
      └──────────┘   └──────────┘
```

## Click Execution Process

```
click_element()
      │
      ▼
┌──────────────┐
│ Scroll into  │
│    view      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Try regular  │
│   click()    │
└──────┬───────┘
       │
  ┌────┴────┐
  │         │
Success   Failed
  │         │
  │         ▼
  │   ┌──────────────┐
  │   │ Try JS click │
  │   │ (fallback)   │
  │   └──────┬───────┘
  │          │
  │     ┌────┴────┐
  │     │         │
  │  Success   Failed
  │     │         │
  └─────┴──┐      │
           │      │
           ▼      ▼
       ┌────────────┐
       │   Return   │
       │ True/False │
       └────────────┘
```

## Real-World Example: IAPD Page

```
HTML Structure:
┌────────────────────────────────────────┐
│ <div class="accordion">                │
│   <div class="accordion-header">       │
│     <h3>Form ADV Part 1 Data Files</h3>│
│   </div>                               │
│   <div class="accordion-content">      │
│     <a href="...zip">October</a>       │
│     <a href="...zip">September</a>     │
│   </div>                               │
│ </div>                                 │
└────────────────────────────────────────┘

Strategy Application:
┌─────────────────────────────────────────┐
│ Strategy 1: class = "accordion-header"  │
│          ↓                              │
│  Finds: <div class="accordion-header">  │
│          ↓                              │
│  Click: Success ✓                       │
│          ↓                              │
│  Content expands                        │
│          ↓                              │
│  ZIP links now visible                  │
└─────────────────────────────────────────┘
```
