// TODO: Define shared API response types, pagination, error shapes

export interface PaginatedResponse<T> {
  // TODO: count, next, previous, results
}

export interface ApiError {
  // TODO: detail, field_errors, non_field_errors
}

export interface AuthTokens {
  // TODO: access, refresh
}

export interface LoginRequest {
  // TODO: identifier (username/email/phone/national_id) + password
}

export interface RegisterRequest {
  // TODO: username, password, email, phone_number, full_name, national_id
}
