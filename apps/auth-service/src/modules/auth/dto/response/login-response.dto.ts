import { PropertyDto } from '@ai-recruit/common';

export class LoginResponseDto {
  @PropertyDto()
  accessToken?: string;

  @PropertyDto()
  refreshToken?: string;

  @PropertyDto()
  email?: string;

  @PropertyDto()
  success?: boolean;
}
