// Copyright (c) Microsoft Corporation. All rights reserved.
// ReflectionHelper.cs

namespace Microsoft.AutoGen.Core;

public sealed class ReflectionHelper
{
    public static bool IsSubclassOfGeneric(Type type, Type genericBaseType)
    {
        while (type != null && type != typeof(object))
        {
            if (genericBaseType == (type.IsGenericType ? type.GetGenericTypeDefinition() : type))
            {
                return true;
            }
            if (type.BaseType == null)
            {
                return false;
            }
            type = type.BaseType;
        }

        return false;
    }
}
