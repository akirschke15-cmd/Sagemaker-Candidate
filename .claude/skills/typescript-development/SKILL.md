# TypeScript Development Skill

## Project Structure
```
project/
├── src/
│   ├── app/              # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── api/
│   ├── components/
│   │   ├── ui/           # Reusable components
│   │   └── features/     # Feature-specific
│   ├── hooks/            # Custom hooks
│   ├── lib/              # Utilities
│   ├── services/         # API calls
│   └── types/            # TypeScript types
├── tests/
│   └── __tests__/
├── package.json
├── tsconfig.json
└── .env.local
```

## React Patterns

### Component Structure
```typescript
// components/ui/Button.tsx
import { forwardRef, ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'rounded font-medium transition-colors',
          {
            'bg-blue-600 text-white hover:bg-blue-700': variant === 'primary',
            'bg-gray-200 text-gray-900 hover:bg-gray-300': variant === 'secondary',
            'bg-red-600 text-white hover:bg-red-700': variant === 'danger',
          },
          {
            'px-3 py-1.5 text-sm': size === 'sm',
            'px-4 py-2': size === 'md',
            'px-6 py-3 text-lg': size === 'lg',
          },
          className
        )}
        disabled={isLoading}
        {...props}
      >
        {isLoading ? <Spinner /> : children}
      </button>
    )
  }
)
Button.displayName = 'Button'
```

### Data Fetching (TanStack Query)
```typescript
// hooks/useUser.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userService } from '@/services/user'
import type { User, UpdateUserDTO } from '@/types/user'

export function useUser(userId: string) {
  return useQuery({
    queryKey: ['user', userId],
    queryFn: () => userService.getById(userId),
  })
}

export function useUpdateUser() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: UpdateUserDTO) => userService.update(data),
    onSuccess: (user) => {
      queryClient.setQueryData(['user', user.id], user)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

### API Service Layer
```typescript
// services/user.ts
import { apiClient } from '@/lib/api-client'
import type { User, CreateUserDTO, UpdateUserDTO } from '@/types/user'

export const userService = {
  async getById(id: string): Promise<User> {
    const response = await apiClient.get<User>(`/api/users/${id}`)
    return response.data
  },
  
  async create(data: CreateUserDTO): Promise<User> {
    const response = await apiClient.post<User>('/api/users', data)
    return response.data
  },
  
  async update(data: UpdateUserDTO): Promise<User> {
    const response = await apiClient.patch<User>(`/api/users/${data.id}`, data)
    return response.data
  },
}
```

### API Client
```typescript
// lib/api-client.ts
import axios, { AxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle auth error
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

## Next.js Patterns

### Server Components
```typescript
// app/users/[id]/page.tsx
import { notFound } from 'next/navigation'
import { getUserById } from '@/lib/data'

interface Props {
  params: { id: string }
}

export default async function UserPage({ params }: Props) {
  const user = await getUserById(params.id)
  
  if (!user) {
    notFound()
  }
  
  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  )
}
```

### Server Actions
```typescript
// app/actions.ts
'use server'

import { revalidatePath } from 'next/cache'
import { z } from 'zod'
import { db } from '@/lib/db'

const updateUserSchema = z.object({
  id: z.string(),
  name: z.string().min(2),
  email: z.string().email(),
})

export async function updateUser(formData: FormData) {
  const data = updateUserSchema.parse({
    id: formData.get('id'),
    name: formData.get('name'),
    email: formData.get('email'),
  })
  
  await db.user.update({
    where: { id: data.id },
    data: { name: data.name, email: data.email },
  })
  
  revalidatePath('/users')
  return { success: true }
}
```

### API Routes
```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { db } from '@/lib/db'

const createUserSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
})

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const data = createUserSchema.parse(body)
    
    const user = await db.user.create({ data })
    
    return NextResponse.json(user, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ errors: error.errors }, { status: 422 })
    }
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
```

## Type Patterns

### Strict Types
```typescript
// types/user.ts
export interface User {
  id: string
  name: string
  email: string
  role: 'admin' | 'user'
  createdAt: Date
}

export interface CreateUserDTO {
  name: string
  email: string
  password: string
}

export interface UpdateUserDTO {
  id: string
  name?: string
  email?: string
}

// Utility types
export type UserWithoutPassword = Omit<User, 'passwordHash'>
export type UserPreview = Pick<User, 'id' | 'name'>
```

### Zod Schemas
```typescript
// lib/validations/user.ts
import { z } from 'zod'

export const userSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

export type UserFormData = z.infer<typeof userSchema>
```

## Common Commands
```bash
# Dev
npm run dev

# Build
npm run build

# Test
npm test
npm run test:watch
npm run test:coverage

# Lint
npm run lint
npm run lint:fix

# Type check
npm run typecheck
```

## Anti-Patterns to Avoid
- ❌ `any` types (use `unknown` + type guards)
- ❌ Non-null assertions `!` (handle nulls properly)
- ❌ Index signatures without validation
- ❌ Side effects in render (use useEffect)
- ❌ Prop drilling (use Context or Zustand)
- ❌ Direct DOM manipulation (use refs)
