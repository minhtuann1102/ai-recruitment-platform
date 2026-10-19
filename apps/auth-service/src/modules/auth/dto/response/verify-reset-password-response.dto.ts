import { PropertyDto } from '@ai-recruit/common';

export class VerifyResetPasswordResponseDto {
  @PropertyDto()
  isValid: boolean;
}
