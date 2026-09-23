using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Runtime.CompilerServices;
using System.Threading;
using BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts.Base;
using BVB.Toolkit.Client.Net;
using Newtonsoft.Json;

namespace BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts;

[GeneratedCode("NJsonSchema", "14.4.0.0 (NJsonSchema v11.3.2.0 (Newtonsoft.Json v13.0.0.0))")]
public class AddMessage : BaseRequest, IReturn<AddMessageResponse>, IReturn, INotifyPropertyChanged
{
	private Guid? a;

	private Guid? b;

	private string c;

	private List<Guid> d = new List<Guid>();

	[CompilerGenerated]
	private PropertyChangedEventHandler e;

	[JsonProperty("replyToMessageID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public Guid? ReplyToMessageID
	{
		get
		{
			short num = -27448;
			short num2 = num;
			num = -27448;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return a;
			}
		}
		set
		{
			int num = default(int);
			Guid? guid = default(Guid?);
			Guid? guid2 = default(Guid?);
			switch (0)
			{
			default:
				while (true)
				{
					short num2;
					switch (num)
					{
					case 6:
						if (guid.HasValue != guid2.HasValue)
						{
							num2 = 4;
							num = num2;
						}
						else
						{
							num2 = 1;
							num = num2;
						}
						continue;
					case 5:
						a = value;
						RaisePropertyChanged("ReplyToMessageID");
						num2 = 8;
						num = num2;
						continue;
					case 8:
						return;
					case 3:
						num2 = 7;
						num = num2;
						continue;
					case 4:
						num2 = 2;
						num = num2;
						continue;
					case 2:
					{
						num2 = 20941;
						short num3 = num2;
						num2 = 20941;
						switch (num3 == num2)
						{
						case false:
						case true:
							goto IL_0242;
						}
						num2 = 0;
						if (num2 == 0)
						{
						}
						goto IL_017d;
					}
					case 0:
						if (!(guid.GetValueOrDefault() != guid2.GetValueOrDefault()))
						{
							return;
						}
						goto IL_017d;
					case 1:
						if (guid.HasValue)
						{
							num2 = 1;
							if (num2 != 0)
							{
							}
							num2 = 0;
							num = num2;
							continue;
						}
						goto IL_0242;
					case 7:
						return;
						IL_0242:
						num2 = 3;
						num = num2;
						continue;
						IL_017d:
						num2 = 5;
						num = num2;
						continue;
					}
					break;
				}
				goto case 0;
			case 0:
			{
				guid = a;
				guid2 = value;
				short num2 = 6;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("replyToConversationID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public Guid? ReplyToConversationID
	{
		get
		{
			short num = -21394;
			short num2 = num;
			num = -21394;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return b;
			}
		}
		set
		{
			int num = default(int);
			Guid? guid = default(Guid?);
			Guid? guid2 = default(Guid?);
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 8:
						if (guid.HasValue != guid2.HasValue)
						{
							short num2 = 1;
							num = num2;
						}
						else
						{
							short num2 = 7;
							num = num2;
						}
						continue;
					case 4:
					{
						b = value;
						RaisePropertyChanged("ReplyToConversationID");
						short num2 = 0;
						num = num2;
						continue;
					}
					case 0:
						return;
					case 6:
					{
						short num2 = 5;
						num = num2;
						continue;
					}
					case 1:
					{
						short num2 = 17300;
						short num3 = num2;
						num2 = 17300;
						switch (num3 == num2)
						{
						case false:
						case true:
							break;
						default:
							num2 = 1;
							if (num2 != 0)
							{
							}
							num2 = 0;
							if (num2 != 0)
							{
							}
							num2 = 3;
							num = num2;
							continue;
						}
						goto case 4;
					}
					case 3:
					{
						short num2 = 4;
						num = num2;
						continue;
					}
					case 2:
						if (!(guid.GetValueOrDefault() != guid2.GetValueOrDefault()))
						{
							return;
						}
						goto case 3;
					case 7:
						if (guid.HasValue)
						{
							short num2 = 2;
							num = num2;
						}
						else
						{
							short num2 = 6;
							num = num2;
						}
						continue;
					case 5:
						return;
					}
					break;
				}
				goto case 0;
			case 0:
			{
				guid = b;
				guid2 = value;
				short num2 = 8;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("body", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string Body
	{
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = 16669;
			short num2 = num;
			num = 16669;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return c;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
				{
					num = -118;
					short num3 = num;
					num = -118;
					switch (num3 == num)
					{
					case false:
					case true:
						return;
					}
					num = 0;
					if (num != 0)
					{
					}
					switch (0)
					{
					default:
						goto end_IL_0084;
					case 0:
						break;
					}
					goto default;
				}
				default:
					num = 1;
					if (num != 0)
					{
					}
					if (c != value)
					{
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
					c = value;
					RaisePropertyChanged("Body");
					num = 2;
					num2 = num;
					break;
				case 2:
					return;
					end_IL_0084:
					break;
				}
			}
		}
	}

	[Required]
	[JsonProperty("attachmentIDs", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public List<Guid> AttachmentIDs
	{
		get
		{
			short num = -31269;
			short num2 = num;
			num = -31269;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return d;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				num = 5059;
				short num3 = num;
				num = 5059;
				switch (num3 == num)
				{
				default:
					num = 1;
					if (num != 0)
					{
					}
					num = 0;
					if (num != 0)
					{
					}
					switch (num2)
					{
					case 0:
						switch (0)
						{
						default:
							goto end_IL_005a;
						case 0:
							break;
						}
						break;
					case 1:
						d = value;
						RaisePropertyChanged("AttachmentIDs");
						num = 2;
						num2 = num;
						goto end_IL_005a;
					case 2:
						return;
					}
					if (d == value)
					{
						return;
					}
					goto case false;
				case false:
				case true:
					{
						num = 1;
						num2 = num;
						break;
					}
					end_IL_005a:
					break;
				}
			}
		}
	}

	public event PropertyChangedEventHandler PropertyChanged
	{
		[CompilerGenerated]
		add
		{
			int num = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					PropertyChangedEventHandler propertyChangedEventHandler3;
					short num2;
					switch (num)
					{
					case 1:
					{
						num2 = 4681;
						short num3 = num2;
						num2 = 4681;
						switch (num3 == num2)
						{
						case false:
						case true:
							continue;
						}
						num2 = 0;
						if (num2 == 0)
						{
						}
						goto IL_00a1;
					}
					case 2:
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num2 = 0;
							num = num2;
							continue;
						}
						goto IL_00a1;
					case 0:
						{
							num2 = 1;
							if (num2 == 0)
							{
							}
							return;
						}
						IL_00a1:
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Combine(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref e, propertyChangedEventHandler3, propertyChangedEventHandler2);
						num2 = 2;
						num = num2;
						continue;
					}
					break;
				}
				goto case 0;
			}
			case 0:
			{
				propertyChangedEventHandler = e;
				short num2 = 1;
				num = num2;
				goto default;
			}
			}
		}
		[CompilerGenerated]
		remove
		{
			int num = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					switch (num)
					{
					case 1:
					{
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Remove(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref e, propertyChangedEventHandler3, propertyChangedEventHandler2);
						short num2 = 2;
						num = num2;
						continue;
					}
					case 2:
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							short num2 = 0;
							num = num2;
							continue;
						}
						goto case 1;
					case 0:
						return;
					}
					break;
				}
				goto case 0;
			}
			case 0:
			{
				short num2 = 11554;
				short num3 = num2;
				num2 = 11554;
				switch (num3 == num2)
				{
				default:
					num2 = 0;
					if (num2 != 0)
					{
					}
					propertyChangedEventHandler = e;
					break;
				case false:
				case true:
					break;
				}
				num2 = 1;
				if (num2 != 0)
				{
				}
				num2 = 1;
				num = num2;
				goto default;
			}
			}
		}
	}

	protected virtual void RaisePropertyChanged([CallerMemberName] string propertyName = null)
	{
		int num = default(int);
		PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
		switch (0)
		{
		default:
			while (true)
			{
				short num2;
				switch (num)
				{
				case 1:
					if (propertyChangedEventHandler == null)
					{
						return;
					}
					goto IL_0044;
				case 2:
				{
					num2 = -5251;
					short num3 = num2;
					num2 = -5251;
					switch (num3 == num2)
					{
					case false:
					case true:
						break;
					default:
						num2 = 0;
						if (num2 != 0)
						{
						}
						propertyChangedEventHandler(this, new PropertyChangedEventArgs(propertyName));
						num2 = 0;
						num = num2;
						continue;
					}
					goto IL_0044;
				}
				case 0:
					{
						num2 = 1;
						if (num2 == 0)
						{
						}
						return;
					}
					IL_0044:
					num2 = 2;
					num = num2;
					continue;
				}
				break;
			}
			goto case 0;
		case 0:
		{
			propertyChangedEventHandler = e;
			short num2 = 1;
			num = num2;
			goto default;
		}
		}
	}
}
