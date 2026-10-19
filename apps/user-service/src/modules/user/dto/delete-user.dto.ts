import { DeleteUserRequest } from '@ai-recruit/common';
import { IsUUID } from 'class-validator';

export class DeleteUserDataDto implements DeleteUserRequest {
  @IsUUID()
  id: string;
}
