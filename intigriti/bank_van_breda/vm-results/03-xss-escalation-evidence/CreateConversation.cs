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
public class CreateConversation : BaseRequest, IReturn<CreateConversationResponse>, IReturn, INotifyPropertyChanged
{
	private string a;

	private string b;

	private string c;

	private string d;

	private List<Guid> e = new List<Guid>();

	[CompilerGenerated]
	private PropertyChangedEventHandler f;

	[JsonProperty("categoryCOID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string CategoryCOID
	{
		get
		{
			short num = 5397;
			short num2 = num;
			num = 5397;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return a;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 2:
					switch (0)
					{
					default:
						continue;
					case 0:
						break;
					}
					break;
				case 0:
				{
					a = value;
					RaisePropertyChanged("CategoryCOID");
					num = -11816;
					short num3 = num;
					num = -11816;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 1;
						num2 = num;
						continue;
					}
					break;
				}
				case 1:
					return;
				}
				num = 1;
				if (num != 0)
				{
				}
				if (a != value)
				{
					num = 0;
					num2 = num;
					continue;
				}
				break;
			}
		}
	}

	[JsonProperty("receiverTypeCOID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string ReceiverTypeCOID
	{
		get
		{
			short num = -4503;
			short num2 = num;
			num = -4503;
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
			short num = 27787;
			short num2 = num;
			num = 27787;
			int num3;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				num3 = num;
				goto IL_0088;
			case false:
			case true:
				{
					num = 1;
					if (num != 0)
					{
					}
					if (b != value)
					{
						num = 0;
						num3 = num;
						goto IL_0088;
					}
					break;
				}
				IL_0088:
				while (true)
				{
					switch (num3)
					{
					case 1:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						break;
					case 0:
						b = value;
						RaisePropertyChanged("ReceiverTypeCOID");
						num = 2;
						num3 = num;
						continue;
					case 2:
						return;
					}
					break;
				}
				goto case false;
			}
		}
	}

	[JsonProperty("subject", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public string Subject
	{
		get
		{
			short num = -990;
			short num2 = num;
			num = -990;
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
				return c;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				num = 1;
				if (num != 0)
				{
				}
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_005a;
					case 0:
						break;
					}
					goto default;
				default:
				{
					num = -1858;
					short num3 = num;
					num = -1858;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						if (c != value)
						{
							num = 2;
							num2 = num;
							break;
						}
						return;
					case false:
					case true:
						return;
					}
					break;
				}
				case 2:
					c = value;
					RaisePropertyChanged("Subject");
					num = 0;
					num2 = num;
					break;
				case 0:
					return;
					end_IL_005a:
					break;
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
			num = 26039;
			short num2 = num;
			num = 26039;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return d;
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
					switch (0)
					{
					default:
						continue;
					case 0:
						break;
					}
					goto default;
				default:
					if (d != value)
					{
						num = 2;
						num2 = num;
						continue;
					}
					return;
				case 2:
					break;
				case 0:
					return;
				}
				while (true)
				{
					num = 1;
					if (num != 0)
					{
					}
					num = 8122;
					short num3 = num;
					num = 8122;
					switch (num3 == num)
					{
					case false:
					case true:
						continue;
					}
					break;
				}
				num = 0;
				if (num != 0)
				{
				}
				d = value;
				RaisePropertyChanged("Body");
				num = 0;
				num2 = num;
			}
		}
	}

	[JsonProperty("attachmentIDs", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required]
	public List<Guid> AttachmentIDs
	{
		get
		{
			short num = -16818;
			short num2 = num;
			num = -16818;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return e;
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
					switch (0)
					{
					default:
						continue;
					case 0:
						break;
					}
					goto default;
				default:
					if (e != value)
					{
						num = 2;
						num2 = num;
						continue;
					}
					break;
				case 2:
					e = value;
					RaisePropertyChanged("AttachmentIDs");
					num = 0;
					num2 = num;
					continue;
				case 0:
					break;
				}
				break;
			}
			while (true)
			{
				num = -24958;
				short num3 = num;
				num = -24958;
				switch (num3 == num)
				{
				case false:
				case true:
					continue;
				}
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num == 0)
				{
				}
				return;
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
			PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
			PropertyChangedEventHandler propertyChangedEventHandler3;
			short num2;
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 0:
						goto IL_00b7;
					case 2:
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num2 = 1;
							num = num2;
							continue;
						}
						goto IL_00b7;
					case 1:
						num2 = 1;
						if (num2 == 0)
						{
						}
						return;
					}
					break;
				}
				goto case 0;
			case 0:
				{
					num2 = -31703;
					short num3 = num2;
					num2 = -31703;
					switch (num3 == num2)
					{
					case false:
					case true:
						goto IL_00b7;
					}
					num2 = 0;
					if (num2 != 0)
					{
					}
					propertyChangedEventHandler = f;
					num2 = 0;
					num = num2;
					goto default;
				}
				IL_00b7:
				propertyChangedEventHandler2 = propertyChangedEventHandler;
				propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Combine(propertyChangedEventHandler2, value);
				propertyChangedEventHandler = Interlocked.CompareExchange(ref f, propertyChangedEventHandler3, propertyChangedEventHandler2);
				num2 = 2;
				num = num2;
				goto default;
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
					short num2;
					switch (num)
					{
					case 2:
					{
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Remove(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref f, propertyChangedEventHandler3, propertyChangedEventHandler2);
						goto IL_005d;
					}
					case 0:
					{
						num2 = -25414;
						short num3 = num2;
						num2 = -25414;
						switch (num3 == num2)
						{
						case false:
						case true:
							break;
						default:
							goto IL_00b8;
						}
						goto IL_005d;
					}
					case 1:
						{
							num2 = 1;
							if (num2 == 0)
							{
							}
							return;
						}
						IL_00b8:
						num2 = 0;
						if (num2 != 0)
						{
						}
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num2 = 1;
							num = num2;
							continue;
						}
						goto case 2;
						IL_005d:
						num2 = 0;
						num = num2;
						continue;
					}
					break;
				}
				goto case 0;
			}
			case 0:
			{
				propertyChangedEventHandler = f;
				short num2 = 2;
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
				switch (num)
				{
				case 0:
					if (propertyChangedEventHandler != null)
					{
						short num2 = 2;
						num = num2;
						continue;
					}
					goto case 1;
				case 2:
				{
					propertyChangedEventHandler(this, new PropertyChangedEventArgs(propertyName));
					short num2 = 1;
					num = num2;
					continue;
				}
				case 1:
				{
					short num2 = -31913;
					short num3 = num2;
					num2 = -31913;
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
						if (num2 == 0)
						{
						}
						return;
					}
					goto case 2;
				}
				}
				break;
			}
			goto case 0;
		case 0:
		{
			propertyChangedEventHandler = f;
			short num2 = 0;
			num = num2;
			goto default;
		}
		}
	}
}
