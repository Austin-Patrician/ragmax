export type AuthUser = {
  user_id: string
  username: string
  route_permissions: string[]
}

export type LoginRequest = {
  username: string
  password: string
}

export type AuthTokenResponse = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: AuthUser
}
