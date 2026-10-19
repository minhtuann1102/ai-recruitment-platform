import { Public } from '@ai-recruit/common';
import { applyDecorators, UseGuards } from '@nestjs/common';
import { RefreshTokenGuard } from '../guards';

export const RefreshToken = () => applyDecorators(Public(), UseGuards(RefreshTokenGuard));
