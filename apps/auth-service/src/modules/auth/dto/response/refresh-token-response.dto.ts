import { PropertyDto } from '@ai-recruit/common';

export class RefreshTokenResponseDto {
  @PropertyDto()
  accessToken: string;
}
