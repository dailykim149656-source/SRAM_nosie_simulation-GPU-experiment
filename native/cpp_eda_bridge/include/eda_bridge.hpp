#pragma once

#include <string>

namespace sram::eda {

class EdaBridge {
public:
    std::string simulateSramJson(const std::string& request_json) const;
    std::string predictLifetimeJson(const std::string& request_json) const;
    std::string optimizeDesignJson(const std::string& request_json) const;
};

}  // namespace sram::eda

