import { FindUserByEmailRequest } from '@ai-recruit/common';
import { IsEmail } from 'class-validator';

export class FindUserByEmailDataDto implements FindUserByEmailRequest {
  @IsEmail()
  email: string;
}
