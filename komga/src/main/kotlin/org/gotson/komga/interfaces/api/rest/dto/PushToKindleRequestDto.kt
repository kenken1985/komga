package org.gotson.komga.interfaces.api.rest.dto

import jakarta.validation.constraints.NotEmpty

data class PushToKindleRequestDto(
  @field:NotEmpty
  val bookIds: List<String>,
)

