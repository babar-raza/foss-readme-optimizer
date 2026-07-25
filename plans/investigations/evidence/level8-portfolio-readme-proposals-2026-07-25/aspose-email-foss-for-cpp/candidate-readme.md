<!-- readme-agent:presentation hash="sha256:b45b00ec3e13a04b46830910acc867aa321dbbcca2aa9761c7e76014f4c306b2" schema="3" inner-bytes="2898" -->
# Aspose.Email FOSS for C++

Aspose.Email FOSS for C++ is a dependency-free C++17 library for deterministic binary email container and message processing without external runtime dependencies.

## At a glance

- **For:** None
- **Problem solved:** None
- **Verified capabilities:** None
- **Verified formats:** None
- **Runtime:** Java unknown+
- **Current verified limitation:** None

## In this README

- [Features](#features)
- [Build](#build)
- [Install](#install)
- [Quick Start](#quick-start)
- [Examples](#examples)

## Installation

Build the verified repository revision from source:

```bash
git clone https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Cpp.git
cd Aspose.Email-FOSS-for-Cpp
git checkout c7252b3e4f6bbec4bbe5e2f50f51eb2a7384eaf2
mvn clean install
```

This path requires JDK unknown+ and Maven. The source build and the minimal example
below were verified together at revision `c7252b3e4f6bbec4bbe5e2f50f51eb2a7384eaf2`.

## Features

- Read CFB containers from file paths, streams, and in-memory byte buffers
- Build and mutate CFB storage/stream trees in user code
- Write deterministic CFB output to files, streams, and byte buffers
- Read and write low-level MSG documents through `msg_reader`, `msg_document`, and `msg_writer`
- Create, edit, save, and reload high-level messages through `mapi_message`
- Work with recipients, regular attachments, and embedded-message attachments
- Load `.eml` into `mapi_message` through an in-repository MIME engine
- Save `mapi_message` back to `.eml` without external MIME libraries

## Build

```powershell
cmake --preset default
cmake --build --preset default
ctest --preset default
```

## Install

```powershell
cmake --install out\build\default --prefix out\install\default
```

## Quick Start

Read a subject from an MSG file:

```cpp
#include <fstream>
#include <iostream>

#include "aspose/email/foss/msg/mapi_message.hpp"

int main()
{
    std::ifstream input("sample.msg", std::ios::binary);
    auto message = aspose::email::foss::msg::mapi_message::from_stream(input);
    std::cout << message.subject() << '\n';
}
```

Create a message and save both MSG and EML:

```cpp
#include <fstream>

#include "aspose/email/foss/msg/mapi_message.hpp"

int main()
{
    auto message = aspose::email::foss::msg::mapi_message::create("Hello", "Body");
    message.set_sender_name("Alice");
    message.set_sender_email_address("alice@example.com");
    message.add_recipient("bob@example.com", "Bob");
    message.add_attachment("note.txt", std::vector<std::uint8_t>{'a', 'b', 'c'}, "text/plain");

    std::ofstream msg_output("hello.msg", std::ios::binary);
    message.save(msg_output);

    std::ofstream eml_output("hello.eml", std::ios::binary);
    message.save_to_eml(eml_output);
}
```

## Examples

Examples are available under `cpp/examples/`:

- `create_msg_and_eml.cpp`
- `msg_reader.cpp`
- `msg_summary.cpp`
<!-- readme-agent:presentation:end -->
